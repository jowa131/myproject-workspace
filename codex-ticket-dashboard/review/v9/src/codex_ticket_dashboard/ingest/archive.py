"""Two-commit archive movement and restart reconciliation."""

from dataclasses import dataclass
from enum import StrEnum, unique
from hashlib import sha256
from pathlib import Path
from typing import Final, Literal, override

from pydantic import TypeAdapter

from codex_ticket_dashboard.domain.identifiers import EventId
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.path_security import DataRootPaths

type ArchiveFailureCode = Literal[
    "ARCHIVE_SOURCE_MISSING",
    "ARCHIVE_INTEGRITY_MISMATCH",
    "ARCHIVE_DUPLICATE_PRESENT",
]
_PENDING_ROWS: Final[TypeAdapter[list[tuple[str, str]]]] = TypeAdapter(
    list[tuple[str, str]]
)


@unique
class CrashPoint(StrEnum):
    """Deterministic process-crash injection points used by recovery tests."""

    AFTER_APPLY_COMMIT = "AFTER_APPLY_COMMIT"
    AFTER_ARCHIVE_MOVE = "AFTER_ARCHIVE_MOVE"


@dataclass(frozen=True, slots=True)
class InjectedCollectorCrashError(RuntimeError):
    """Synthetic process interruption carrying no event payload."""

    point: CrashPoint

    @override
    def __str__(self) -> str:
        return self.point.value


@dataclass(frozen=True, slots=True)
class ArchiveCommand:
    """Applied receipt and source path needed for phase-two archive commit."""

    event_id: EventId
    source: Path
    expected_sha256: str
    crash_at: CrashPoint | None = None


@dataclass(frozen=True, slots=True)
class ArchiveResult:
    """Archive reconciliation outcome."""

    event_id: EventId
    archived: bool
    failure_code: ArchiveFailureCode | None = None


@dataclass(frozen=True, slots=True)
class PendingArchive:
    """Durable APPLIED+PENDING receipt awaiting filesystem reconciliation."""

    event_id: EventId
    expected_sha256: str


def complete_archive(
    database: Database,
    paths: DataRootPaths,
    command: ArchiveCommand,
) -> ArchiveResult:
    """Move one applied source atomically and commit ARCHIVED second."""
    if command.crash_at is CrashPoint.AFTER_APPLY_COMMIT:
        raise InjectedCollectorCrashError(command.crash_at)
    destination = paths.archive / command.source.name
    if destination.exists():
        return _fail(database, command.event_id, "ARCHIVE_DUPLICATE_PRESENT")
    if _digest(command.source) != command.expected_sha256:
        return _fail(database, command.event_id, "ARCHIVE_INTEGRITY_MISMATCH")
    _ = command.source.rename(destination)
    if command.crash_at is CrashPoint.AFTER_ARCHIVE_MOVE:
        raise InjectedCollectorCrashError(command.crash_at)
    _mark_archived(database, command.event_id)
    return ArchiveResult(event_id=command.event_id, archived=True)


def load_pending_archives(database: Database) -> tuple[PendingArchive, ...]:
    """Load all receipts requiring startup archive reconciliation."""
    with database.connection() as connection:
        rows = _PENDING_ROWS.validate_python(
            connection.execute(
                """SELECT event_id,archive_payload_sha256 FROM ingest_receipts
                WHERE state='APPLIED' AND archive_state='PENDING' ORDER BY ingest_seq,event_id"""
            ).fetchall()
        )
    return tuple(PendingArchive(EventId(str(row[0])), str(row[1])) for row in rows)


def reconcile_archive(
    database: Database,
    paths: DataRootPaths,
    pending: PendingArchive,
) -> ArchiveResult:
    """Resolve the two crash windows without repeating event projection."""
    sources = _matching_files(
        (paths.incoming, paths.pending_identity, paths.pending_dependency), pending.event_id
    )
    archives = _matching_files((paths.archive,), pending.event_id)
    if len(sources) + len(archives) == 0:
        return _fail(database, pending.event_id, "ARCHIVE_SOURCE_MISSING")
    if len(sources) > 1 or len(archives) > 1 or (sources and archives):
        return _fail(database, pending.event_id, "ARCHIVE_DUPLICATE_PRESENT")
    candidate = next(iter(archives or sources))
    if _digest(candidate) != pending.expected_sha256:
        return _fail(database, pending.event_id, "ARCHIVE_INTEGRITY_MISMATCH")
    if sources:
        source = next(iter(sources))
        _ = source.rename(paths.archive / source.name)
    _mark_archived(database, pending.event_id)
    return ArchiveResult(event_id=pending.event_id, archived=True)


def _matching_files(directories: tuple[Path, ...], event_id: EventId) -> tuple[Path, ...]:
    suffix = f"__{event_id}.json"
    return tuple(
        path
        for directory in directories
        for path in sorted(directory.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.name.endswith(suffix)
    )


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _mark_archived(database: Database, event_id: EventId) -> None:
    with database.transaction() as connection:
        _ = connection.execute(
            """UPDATE ingest_receipts SET archive_state='ARCHIVED',archive_error_code=NULL
            WHERE event_id=? AND state='APPLIED' AND archive_state='PENDING'""",
            (event_id,),
        )


def _mark_failed(database: Database, event_id: EventId, code: ArchiveFailureCode) -> None:
    with database.transaction() as connection:
        _ = connection.execute(
            """UPDATE ingest_receipts SET archive_state='FAILED',archive_error_code=?
            WHERE event_id=? AND state='APPLIED' AND archive_state='PENDING'""",
            (code, event_id),
        )


def _fail(database: Database, event_id: EventId, code: ArchiveFailureCode) -> ArchiveResult:
    _mark_failed(database, event_id, code)
    return ArchiveResult(event_id=event_id, archived=False, failure_code=code)
