"""Single-writer collector orchestration without polling or retry loops."""

import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Final, assert_never, final

from pydantic import JsonValue, TypeAdapter, ValidationError

from codex_ticket_dashboard.compliance.runtime_authority import VerifiedRuntimeAuthority
from codex_ticket_dashboard.domain.identifiers import EventId, ProjectId
from codex_ticket_dashboard.ingest import authority_models as authority
from codex_ticket_dashboard.ingest.archive import (
    ArchiveCommand,
    CrashPoint,
    complete_archive,
)
from codex_ticket_dashboard.ingest.dead_letter import (
    CollectedEvent,
    PrivacyRejected,
    SafeDocument,
    SafeJsonRejected,
    inspect_raw_json,
    move_to_dead_letter,
    parse_collected_event,
    parse_rejection_header,
    persist_rejection,
)
from codex_ticket_dashboard.ingest.dependencies import (
    PendingEventReceipt,
    admit_event_dependencies,
)
from codex_ticket_dashboard.ingest.identity import BootstrapResolution
from codex_ticket_dashboard.ingest.lifecycle_identity import resolve_lifecycle_identity
from codex_ticket_dashboard.ingest.privacy_disposition import dispose_privacy_source
from codex_ticket_dashboard.ingest.projector import apply_event
from codex_ticket_dashboard.ingest.recovery import (
    CollectorReport,
    IdentityLink,
    ReportBuilder,
    find_pending_event,
    identity_replay_targets,
    move_failed_files,
    move_if_absent,
    persist_identity_pending,
    recover_startup,
    scan_spool,
    waiting_children,
)
from codex_ticket_dashboard.lifecycle.contracts import LIFECYCLE_EVENT_TYPES
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.path_security import DataRootPaths


@dataclass(frozen=True, slots=True)
class IdentityReplayRequest:
    """Validated bootstrap result bound to its applied resolution event."""

    resolution: BootstrapResolution
    resolution_event_id: EventId


@dataclass(frozen=True, slots=True)
class _CollectContext:
    mapped_project: ProjectId | None = None
    identity_link: IdentityLink | None = None
    crash_at: CrashPoint | None = None


_DEFAULT_CONTEXT: Final = _CollectContext()
_RECEIPT_MATCH: Final[TypeAdapter[tuple[str, str] | None]] = TypeAdapter(tuple[str, str] | None)


type _Rejection = tuple[JsonValue, str, str]
type _ParsedSource = tuple[bytes, JsonValue, CollectedEvent]


@dataclass(frozen=True, slots=True)
class _ReadySource:
    path: Path
    parsed: _ParsedSource
    project_id: ProjectId | None
    context: _CollectContext


@final
class Collector:
    """Own the only SQLite writer and deterministic spool replay path."""

    def __init__(
        self,
        database: Database,
        paths: DataRootPaths,
        *,
        authority_seam: authority.AuthoritySeam = authority.DEFAULT_AUTHORITY_SEAM,
    ) -> None:
        """Bind the collector to one database and one protected spool root."""
        self._database = database
        self._paths = paths
        self._authority_seam = authority_seam

    def startup_scan(self, *, crash_at: CrashPoint | None = None) -> CollectorReport:
        """Run archive reconciliation and one startup scan of all pending areas."""
        return self._run_scan(crash_at)

    def bootstrap_runtime(self, authority: VerifiedRuntimeAuthority) -> None:
        """Initialize approved registry/policy through the collector's single writer."""
        from codex_ticket_dashboard.ingest.runtime_bootstrap import bootstrap_runtime  # noqa: PLC0415

        bootstrap_runtime(self._database, authority)

    def notification_hint(self) -> CollectorReport:
        """Treat a filesystem notification as a hint for one complete rescan."""
        return self._run_scan(None)

    def replay_identity(self, request: IdentityReplayRequest) -> CollectorReport:
        """Replay only files for an already validated exact identity mapping."""
        builder = ReportBuilder()
        targets = identity_replay_targets(self._paths, request.resolution)
        if targets.project_id is None:
            return builder.report()
        context = _CollectContext(
            targets.project_id,
            IdentityLink(request.resolution_event_id),
        )
        for path in targets.paths:
            self._collect_path(path, builder, context)
        resolve_lifecycle_identity(self._database, request.resolution, request.resolution_event_id)
        return builder.report()

    def _run_scan(self, crash_at: CrashPoint | None) -> CollectorReport:
        builder = ReportBuilder()
        try:
            recovery = recover_startup(self._database, self._paths)
            builder.recovered.extend(recovery.recovered_event_ids)
            builder.archive_failures.extend(recovery.failure_codes)
            builder.tmp_files.extend(recovery.tmp_file_names)
            for path in scan_spool(self._paths):
                if path.exists():
                    self._collect_path(path, builder, _CollectContext(crash_at=crash_at))
        except sqlite3.Error:
            builder.database_unavailable = True
        return builder.report()

    def _collect_path(
        self,
        path: Path,
        builder: ReportBuilder,
        context: _CollectContext = _DEFAULT_CONTEXT,
    ) -> None:
        parsed = self._parse_source(path, builder)
        if parsed is None:
            return
        event = parsed[2]
        if self._is_existing_or_collision(event, builder):
            return
        effective_project = context.mapped_project or event.project_id
        lifecycle = (
            event.event_type.value in LIFECYCLE_EVENT_TYPES
            and isinstance(event.payload.root, dict)
            and event.payload.root.get("lifecycle_version") == 1
        )
        if effective_project is None and not lifecycle:
            persist_identity_pending(self._database, self._paths, path, event)
            return
        if self._dependency_stops(path, event, builder):
            return
        self._apply_source(_ReadySource(path, parsed, effective_project, context), builder)

    def _dependency_stops(
        self,
        path: Path,
        event: CollectedEvent,
        builder: ReportBuilder,
    ) -> bool:
        dependency = admit_event_dependencies(
            self._database,
            PendingEventReceipt(event.event_id, event.idempotency_key, event.payload_digest),
            event.depends_on_event_ids,
        )
        if dependency.failed_event_ids:
            builder.failed.extend(
                item for item in dependency.failed_event_ids if item not in builder.failed
            )
            move_failed_files(self._paths, dependency.failed_event_ids)
            return True
        if dependency.deferred:
            move_if_absent(path, self._paths.pending_dependency)
            return True
        return False

    def _apply_source(self, source: _ReadySource, builder: ReportBuilder) -> None:
        event = source.parsed[2]
        raw = source.parsed[0]
        try:
            newly_applied = apply_event(
                self._database,
                authority.ApplyCommand(
                    event,
                    source.project_id,
                    sha256(raw).hexdigest(),
                    source.context.identity_link,
                    self._authority_seam,
                ),
            )
        except authority.ProjectionSchemaError as error:
            self._reject(
                source.path,
                builder,
                (source.parsed[1], error.code, error.field_path),
            )
            return
        except authority.IdempotencyCollisionError:
            builder.collisions.append(event.event_id)
            return
        if newly_applied:
            builder.processed.append(event.event_id)
        children = waiting_children(self._database, event.event_id)
        archive = complete_archive(
            self._database,
            self._paths,
            ArchiveCommand(
                event.event_id,
                source.path,
                sha256(raw).hexdigest(),
                source.context.crash_at,
            ),
        )
        if archive.failure_code is not None:
            builder.archive_failures.append(archive.failure_code)
            return
        for child_id in children:
            child = find_pending_event(self._paths, child_id)
            if child is not None:
                self._collect_path(child, builder)

    def _parse_source(self, path: Path, builder: ReportBuilder) -> _ParsedSource | None:
        raw = path.read_bytes()
        inspected = inspect_raw_json(raw)
        match inspected:
            case PrivacyRejected():
                dispose_privacy_source(path, self._paths)
                builder.privacy_files.append(path.name)
                return None
            case SafeJsonRejected():
                return None
            case SafeDocument(value=value):
                try:
                    event = parse_collected_event(value)
                except ValidationError:
                    self._reject(path, builder, (value, "EVENT_SCHEMA_INVALID", "$"))
                    return None
                return raw, value, event
            case unreachable:
                assert_never(unreachable)

    def _reject(
        self,
        path: Path,
        builder: ReportBuilder,
        rejection: _Rejection,
    ) -> None:
        value, code, field_path = rejection
        header = parse_rejection_header(value)
        if header is None:
            return
        failed = persist_rejection(self._database, header, code, field_path)
        builder.rejected.append(header.event_id)
        builder.failed.extend(failed)
        _ = move_to_dead_letter(path, self._paths.dead_letter)
        move_failed_files(self._paths, failed)

    def _is_existing_or_collision(self, event: CollectedEvent, builder: ReportBuilder) -> bool:
        with self._database.connection() as connection:
            row = _RECEIPT_MATCH.validate_python(
                connection.execute(
                    "SELECT payload_digest,state FROM ingest_receipts WHERE idempotency_key=?",
                    (event.idempotency_key,),
                ).fetchone()
            )
        if row is None:
            return False
        if str(row[0]) != event.payload_digest:
            builder.collisions.append(event.event_id)
            return True
        return str(row[1]) in {"APPLIED", "REJECTED", "DEPENDENCY_FAILED"}
