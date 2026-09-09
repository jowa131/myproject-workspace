"""Existing-file SQLite observation reads without migration or writable connections."""

import sqlite3
from collections.abc import Generator
from contextlib import ExitStack, closing, contextmanager
from pathlib import Path
from typing import Literal, final, override

import codex_ticket_dashboard.storage.win32_native as native
from codex_ticket_dashboard.storage.path_security import (
    parse_local_fixed_path,
    validate_secure_path,
)
from codex_ticket_dashboard.storage.win32_handles import verify_handle


@final
class ReadOnlyObservationError(OSError):
    """Return no database path, SQL, or corrupt source bytes to observer callers."""

    code: Literal["OBSERVATION_DATABASE_UNAVAILABLE"] = "OBSERVATION_DATABASE_UNAVAILABLE"

    def __init__(self) -> None:
        """Expose a fixed code while retaining normal Python exception semantics."""
        super().__init__(self.code)

    @override
    def __str__(self) -> str:
        return self.code


@contextmanager
def _pin(path: Path, approved_root: Path, *, directory: bool) -> Generator[Path]:
    canonical = validate_secure_path(path, approved_root)
    flags = native.FILE_FLAG_OPEN_REPARSE_POINT
    if directory:
        flags |= native.FILE_FLAG_BACKUP_SEMANTICS
    value = native.create_file(
        native.CREATE_FILE,
        str(canonical),
        native.FILE_READ_ATTRIBUTES,
        native.OPEN_EXISTING,
        flags,
    )
    if value == native.INVALID_HANDLE_VALUE:
        raise ReadOnlyObservationError
    handle = native.WinHandle(value)
    try:
        yield verify_handle(handle, canonical)
    finally:
        _ = native.close_native(native.CLOSE_HANDLE, handle)


@contextmanager
def read_observation_database(path: Path, approved_root: Path) -> Generator[sqlite3.Connection]:
    """Pin existing protected ancestors/file and provide one query-only SQLite snapshot."""
    try:
        root = parse_local_fixed_path(approved_root)
        database = parse_local_fixed_path(path)
        relative = database.relative_to(root)
        with ExitStack() as pins:
            canonical_root = pins.enter_context(_pin(root, root, directory=True))
            canonical_database = validate_secure_path(database, root)
            if canonical_database.relative_to(canonical_root) != relative:
                raise ReadOnlyObservationError
            parent = canonical_root
            for component in relative.parts[:-1]:
                parent /= component
                parent = pins.enter_context(_pin(parent, canonical_root, directory=True))
            pinned_database = pins.enter_context(
                _pin(canonical_database, canonical_root, directory=False),
            )
            with closing(
                sqlite3.connect(
                    pinned_database.as_uri() + "?mode=ro",
                    uri=True,
                    isolation_level=None,
                    timeout=0.1,
                )
            ) as connection:
                _ = connection.execute("PRAGMA query_only=ON")
                _ = connection.execute("PRAGMA schema_version")
                _ = connection.execute("BEGIN")
                yield connection
    except (OSError, sqlite3.Error, ValueError):
        raise ReadOnlyObservationError from None
