"""Startup archive reconciliation and bounded spool discovery."""

import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import assert_never

from pydantic import TypeAdapter, ValidationError

from codex_ticket_dashboard.domain.identifiers import EventId, ProjectId
from codex_ticket_dashboard.ingest.archive import (
    ArchiveFailureCode,
    load_pending_archives,
    reconcile_archive,
)
from codex_ticket_dashboard.ingest.dead_letter import (
    CollectedEvent,
    PrivacyRejected,
    SafeDocument,
    SafeJsonRejected,
    inspect_raw_json,
    move_to_dead_letter,
    parse_collected_event,
)
from codex_ticket_dashboard.ingest.identity import BootstrapCode, BootstrapResolution
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.path_security import DataRootPaths

_EVENT_ROWS: TypeAdapter[list[tuple[str]]] = TypeAdapter(list[tuple[str]])


@dataclass(frozen=True, slots=True)
class StartupRecovery:
    """Read-once startup recovery observations."""

    recovered_event_ids: tuple[EventId, ...]
    failure_codes: tuple[ArchiveFailureCode, ...]
    tmp_file_names: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IdentityReplayTargets:
    """Exact pending paths selected by a validated bootstrap result."""

    project_id: ProjectId | None
    paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class IdentityLink:
    """Validated identity replay audit link."""

    resolution_event_id: EventId


@dataclass(frozen=True, slots=True)
class IdentityLinkWrite:
    """Atomic observation mapping written with the replayed event."""

    event: CollectedEvent
    project_id: ProjectId
    link: IdentityLink
    ingest_seq: int


@dataclass(frozen=True, slots=True)
class CollectorReport:
    """One bounded scan outcome with no payload or path values."""

    processed_event_ids: tuple[EventId, ...] = ()
    failed_event_ids: tuple[EventId, ...] = ()
    rejected_event_ids: tuple[EventId, ...] = ()
    collision_event_ids: tuple[EventId, ...] = ()
    archive_recovered_event_ids: tuple[EventId, ...] = ()
    archive_failure_codes: tuple[str, ...] = ()
    privacy_rejected_file_names: tuple[str, ...] = ()
    tmp_warning_file_names: tuple[str, ...] = ()
    database_unavailable: bool = False


class ReportBuilder:
    """Mutable accumulator scoped to one synchronous collector scan."""

    def __init__(self) -> None:
        """Create empty metadata lists for one synchronous run."""
        self.processed: list[EventId] = []
        self.failed: list[EventId] = []
        self.rejected: list[EventId] = []
        self.collisions: list[EventId] = []
        self.recovered: list[EventId] = []
        self.archive_failures: list[str] = []
        self.privacy_files: list[str] = []
        self.tmp_files: list[str] = []
        self.database_unavailable: bool = False

    def report(self) -> CollectorReport:
        """Freeze accumulated metadata for the caller."""
        return CollectorReport(
            tuple(self.processed),
            tuple(self.failed),
            tuple(self.rejected),
            tuple(self.collisions),
            tuple(self.recovered),
            tuple(self.archive_failures),
            tuple(self.privacy_files),
            tuple(self.tmp_files),
            self.database_unavailable,
        )


def recover_startup(database: Database, paths: DataRootPaths) -> StartupRecovery:
    """Reconcile APPLIED+PENDING receipts and surface stale tmp files without mutation."""
    recovered: list[EventId] = []
    failures: list[ArchiveFailureCode] = []
    for pending in load_pending_archives(database):
        result = reconcile_archive(database, paths, pending)
        if result.archived:
            recovered.append(result.event_id)
        elif result.failure_code is not None:
            failures.append(result.failure_code)
    tmp_names = tuple(
        path.name
        for path in sorted(paths.tmp.iterdir(), key=lambda item: item.name)
        if path.is_file()
    )
    return StartupRecovery(tuple(recovered), tuple(failures), tmp_names)


def scan_spool(paths: DataRootPaths) -> tuple[Path, ...]:
    """Return one deterministic snapshot of incoming and both pending areas."""
    candidates = tuple(
        path
        for directory in (paths.incoming, paths.pending_identity, paths.pending_dependency)
        for path in directory.iterdir()
        if path.is_file() and path.suffix == ".json"
    )
    return tuple(sorted(candidates, key=lambda path: (path.name, str(path.parent))))


def find_pending_event(paths: DataRootPaths, event_id: EventId) -> Path | None:
    """Find one exact pending event file for targeted dependency replay."""
    suffix = f"__{event_id}.json"
    matches = tuple(path for path in scan_spool(paths) if path.name.endswith(suffix))
    return matches[0] if len(matches) == 1 else None


def waiting_children(database: Database, parent: EventId) -> tuple[EventId, ...]:
    """Return only pending events whose reverse index names the applied parent."""
    with database.connection() as connection:
        rows = _EVENT_ROWS.validate_python(
            connection.execute(
                """SELECT event_id FROM pending_dependencies
                WHERE dependency_event_id=? ORDER BY event_id""",
                (parent,),
            ).fetchall()
        )
    return tuple(EventId(row[0]) for row in rows)


def record_identity_link(connection: sqlite3.Connection, write: IdentityLinkWrite) -> None:
    """Link the immutable source event to its exact accepted resolution."""
    _ = connection.execute(
        """UPDATE project_observations SET resolution_state='RESOLVED',
        candidate_project_id=?,last_observed_at=? WHERE id=?""",
        (
            write.project_id,
            write.event.occurred_at.isoformat(),
            write.event.project_observation_id,
        ),
    )
    _ = connection.execute(
        """INSERT INTO event_project_resolutions VALUES (?,?,?,?,?)""",
        (
            write.event.event_id,
            write.event.project_observation_id,
            write.link.resolution_event_id,
            write.project_id,
            write.ingest_seq,
        ),
    )


def persist_identity_pending(
    database: Database,
    paths: DataRootPaths,
    source: Path,
    event: CollectedEvent,
) -> None:
    """Persist one identity index and move only its immutable source file."""
    with database.transaction() as connection:
        _ = connection.execute(
            """INSERT INTO ingest_receipts(idempotency_key,event_id,payload_digest,state)
            VALUES (?,?,?,'PENDING_IDENTITY')
            ON CONFLICT(idempotency_key) DO UPDATE SET state='PENDING_IDENTITY'""",
            (event.idempotency_key, event.event_id, event.payload_digest),
        )
        fingerprint = "sha256:" + sha256(event.project_observation_id.encode()).hexdigest()
        _ = connection.execute(
            """INSERT INTO project_observations VALUES (?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET last_observed_at=excluded.last_observed_at""",
            (
                event.project_observation_id,
                event.project_resolution_state.value,
                fingerprint,
                None,
                event.occurred_at.isoformat(),
                event.occurred_at.isoformat(),
            ),
        )
    destination = paths.pending_identity / source.name
    if source.parent != paths.pending_identity and not destination.exists():
        _ = source.rename(destination)


def read_safe_event(path: Path) -> CollectedEvent | None:
    """Read a pending file only when privacy and envelope parsing both pass."""
    inspected = inspect_raw_json(path.read_bytes())
    match inspected:
        case SafeDocument(value=value):
            try:
                return parse_collected_event(value)
            except ValidationError:
                return None
        case PrivacyRejected() | SafeJsonRejected():
            return None
        case unreachable:
            assert_never(unreachable)


def identity_replay_targets(
    paths: DataRootPaths,
    resolution: BootstrapResolution,
) -> IdentityReplayTargets:
    """Select only the pending observation named by an accepted mapping."""
    match resolution.code:
        case BootstrapCode.PROJECT_IDENTITY_RESOLUTION_REJECTED:
            return IdentityReplayTargets(None, ())
        case BootstrapCode.APPLIED:
            mapping = resolution.mapping
            if mapping is None:
                return IdentityReplayTargets(None, ())
            matches = tuple(
                path
                for path in scan_spool(paths)
                if (event := read_safe_event(path)) is not None
                and event.project_observation_id == mapping.observation_id
            )
            return IdentityReplayTargets(mapping.project_id, matches)
        case unreachable:
            assert_never(unreachable)


def move_if_absent(source: Path, directory: Path) -> None:
    """Move a spool file without overwriting an existing destination."""
    if source.parent == directory:
        return
    destination = directory / source.name
    if not destination.exists():
        _ = source.rename(destination)


def move_failed_files(paths: DataRootPaths, event_ids: tuple[EventId, ...]) -> None:
    """Move terminal dependency files to dead-letter without deleting duplicates."""
    for event_id in event_ids:
        path = find_pending_event(paths, event_id)
        if path is not None:
            _ = move_to_dead_letter(path, paths.dead_letter)
