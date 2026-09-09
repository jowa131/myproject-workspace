"""SQLite connection, transaction, and forward migration boundary."""

import re
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import TracebackType
from typing import Final, Literal, assert_never, final

from pydantic import TypeAdapter

from codex_ticket_dashboard.storage.models import (
    ComplianceGateChange,
    DatabaseConfig,
    IngestIssueChange,
    InvalidDatabaseConfigError,
    Migration,
    MigrationChecksumMismatchError,
    MigrationFailedError,
    ProjectChange,
    ProjectionWrite,
    TicketChange,
    UnsupportedSchemaVersionError,
)
from codex_ticket_dashboard.storage.path_security import SqliteAclGuard

DEFAULT_BUSY_TIMEOUT_MS: Final = 5_000
MAX_BUSY_TIMEOUT_MS: Final = 60_000
MIGRATION_PATTERN: Final = re.compile(r"^(?P<version>[0-9]{3})_(?P<name>[a-z0-9_]+)\.sql$")


_MIGRATION_ROWS = TypeAdapter(list[tuple[int, str]])


@final
class _Transaction:
    """Own one explicit SQLite transaction without generator exception mutation."""

    def __init__(self, connection: sqlite3.Connection, *, read_only: bool = False) -> None:
        """Retain the configured connection for one transaction scope."""
        self._connection = connection
        self._read_only = read_only

    def __enter__(self) -> sqlite3.Connection:
        if self._read_only:
            _ = self._connection.execute("PRAGMA query_only = ON")
            _ = self._connection.execute("BEGIN")
        else:
            _ = self._connection.execute("BEGIN IMMEDIATE")
        return self._connection

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: TracebackType | None,
    ) -> Literal[False]:
        try:
            if exception_type is None:
                self._connection.commit()
            elif self._connection.in_transaction:
                self._connection.rollback()
        finally:
            self._connection.close()
        return False


@final
class Database:
    """Own configured SQLite connections and migration transactions."""

    def __init__(self, config: DatabaseConfig) -> None:
        """Validate settings before opening any database path."""
        if not 0 < config.busy_timeout_ms <= MAX_BUSY_TIMEOUT_MS:
            raise InvalidDatabaseConfigError(field_path="busy_timeout_ms")
        self._config = config
        self._acl_guard = SqliteAclGuard(config.path)

    @property
    def path(self) -> Path:
        """Expose the configured filename without opening or changing storage."""
        return self._config.path

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection]:
        """Open a configured autocommit connection and always close it."""
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def transaction(self) -> _Transaction:
        """Run an immediate transaction with deterministic rollback."""
        return _Transaction(self._connect())

    def read_transaction(self) -> _Transaction:
        """Open a deferred query-only transaction without reserving the writer lock."""
        return _Transaction(self._connect(), read_only=True)

    def migrate(self) -> None:
        """Apply every pending migration once and reject schema drift."""
        migrations = self._load_migrations()
        supported_version = migrations[-1].version if migrations else 0
        with self.connection() as connection:
            _ = connection.execute(
                """CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            rows = _MIGRATION_ROWS.validate_python(
                connection.execute(
                    "SELECT version, checksum FROM schema_migrations ORDER BY version"
                ).fetchall()
            )
            applied = tuple(rows)
        migration_by_version = {migration.version: migration for migration in migrations}
        for version, checksum in applied:
            migration = migration_by_version.get(version)
            if migration is None or version > supported_version:
                raise UnsupportedSchemaVersionError(version=version)
            if checksum != migration.checksum:
                raise MigrationChecksumMismatchError(version=version)
        applied_versions = {version for version, _checksum in applied}
        for migration in migrations:
            if migration.version not in applied_versions:
                self._apply_migration(migration)

    def _connect(self) -> sqlite3.Connection:
        self._acl_guard.secure_present(create_database=True)
        connection = sqlite3.connect(
            self._config.path, timeout=self._config.busy_timeout_ms / 1000, isolation_level=None
        )
        try:
            _ = connection.execute("PRAGMA foreign_keys = ON")
            _ = connection.execute(f"PRAGMA busy_timeout = {self._config.busy_timeout_ms}")
            _ = connection.execute("PRAGMA journal_mode = WAL")
            self._acl_guard.secure_present(create_database=False)
        except (OSError, sqlite3.Error):
            connection.close()
            raise
        return connection

    def _load_migrations(self) -> tuple[Migration, ...]:
        directory = self._config.migrations_path or Path(__file__).with_name("migrations")
        migrations: list[Migration] = []
        for path in sorted(directory.glob("*.sql")):
            match = MIGRATION_PATTERN.fullmatch(path.name)
            if match is None:
                continue
            sql = path.read_text(encoding="utf-8")
            migrations.append(
                Migration(
                    version=int(match.group("version")),
                    name=match.group("name"),
                    checksum=sha256(sql.encode()).hexdigest(),
                    sql=sql,
                )
            )
        return tuple(migrations)

    def _apply_migration(self, migration: Migration) -> None:
        try:
            with self.transaction() as connection:
                for statement in _split_statements(migration.sql):
                    _ = connection.execute(statement)
                _ = connection.execute(
                    "INSERT INTO schema_migrations(version, name, checksum) VALUES (?, ?, ?)",
                    (migration.version, migration.name, migration.checksum),
                )
        except sqlite3.Error as error:
            raise MigrationFailedError(version=migration.version) from error

    def write_projection(
        self,
        connection: sqlite3.Connection,
        write: ProjectionWrite,
    ) -> None:
        """Write a current projection; migration triggers preserve its history."""
        match write.change:
            case ProjectChange():
                _write_project(connection, write.ingest_seq, write.change)
            case TicketChange():
                _write_ticket(connection, write, write.change)
            case ComplianceGateChange():
                _write_gate(connection, write.ingest_seq, write.change)
            case IngestIssueChange():
                _write_issue(connection, write.ingest_seq, write.change)
            case unreachable:
                assert_never(unreachable)


def _split_statements(sql: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for line in sql.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        statements.append(buffer.strip())
    return tuple(statements)


def _write_project(connection: sqlite3.Connection, seq: int, change: ProjectChange) -> None:
    _ = connection.execute(
        """INSERT INTO projects VALUES (?,?,?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET
        label=excluded.label,logical_root_key=excluded.logical_root_key,repo_key=excluded.repo_key,
        identity_source=excluded.identity_source,
        identity_source_hash=excluded.identity_source_hash,version=projects.version+1""",
        (
            change.project_id,
            change.label,
            change.logical_root_key,
            change.repo_key,
            change.identity_source,
            change.identity_source_hash,
            seq,
        ),
    )


def _write_ticket(
    connection: sqlite3.Connection, write: ProjectionWrite, change: TicketChange
) -> None:
    timestamp = write.occurred_at.isoformat()
    _ = connection.execute(
        """INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)
        ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id,title=excluded.title,
        record_type=excluded.record_type,status=excluded.status,
        needs_triage=excluded.needs_triage,summary=excluded.summary,
        next_step=excluded.next_step,updated_at=excluded.updated_at,
        closed_at=excluded.closed_at,closed_reason=excluded.closed_reason,version=tickets.version+1""",
        (
            change.ticket_id,
            change.project_id,
            change.title,
            change.record_type.value,
            change.status.value,
            int(change.needs_triage),
            change.summary,
            change.next_step,
            timestamp,
            timestamp,
            write.ingest_seq,
            None if change.closed_at is None else change.closed_at.isoformat(),
            change.closed_reason,
        ),
    )


def _write_gate(connection: sqlite3.Connection, seq: int, change: ComplianceGateChange) -> None:
    _ = connection.execute(
        """INSERT INTO compliance_gates VALUES (?,?,?,?,?,?,?,?,?,?,1)
        ON CONFLICT(id) DO UPDATE SET project_id=excluded.project_id,ticket_id=excluded.ticket_id,
        work_item_id=excluded.work_item_id,gate_type=excluded.gate_type,
        requirement=excluded.requirement,status=excluded.status,evidence_ref=excluded.evidence_ref,
        evidence_hash=excluded.evidence_hash,version=compliance_gates.version+1""",
        (
            change.gate_id,
            change.project_id,
            change.ticket_id,
            change.work_item_id,
            change.gate_type.value,
            change.requirement.value,
            change.status.value,
            change.evidence_ref,
            change.evidence_hash,
            seq,
        ),
    )


def _write_issue(connection: sqlite3.Connection, seq: int, change: IngestIssueChange) -> None:
    _ = connection.execute(
        """INSERT INTO ingest_issues VALUES (?,?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET
        event_id=excluded.event_id,code=excluded.code,field_path=excluded.field_path,
        state=excluded.state,version=ingest_issues.version+1""",
        (change.issue_id, change.event_id, change.code, change.field_path, change.state.value, seq),
    )
