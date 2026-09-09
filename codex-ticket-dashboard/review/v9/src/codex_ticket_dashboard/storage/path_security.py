"""Windows local-path and owner-only ACL enforcement."""

import ctypes
import ntpath
import os
import re
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, final, override

import codex_ticket_dashboard.storage.win32_native as native
from codex_ticket_dashboard.storage.locks import (
    apply_owner_only_acl,
    inspect_owner_only_acl,
)
from codex_ticket_dashboard.storage.win32_handles import verify_handle

__all__ = [
    "DataRootPaths",
    "PathSecurityError",
    "SqliteAclGuard",
    "apply_owner_only_acl",
    "data_root_paths",
    "initialize_data_root",
    "inspect_owner_only_acl",
    "parse_local_fixed_path",
    "secure_owner_only_file",
    "validate_secure_path",
]

_DRIVE_FIXED: Final = 3
_UNRESOLVED_ENV: Final = re.compile(r"%[^%]+%|\$\{[^}]+\}|\$[A-Za-z_][A-Za-z0-9_]*")

type PathSecurityCode = Literal[
    "WINDOWS_REQUIRED", "PATH_UNRESOLVED_ENV", "PATH_NOT_ABSOLUTE",
    "PATH_UNC_FORBIDDEN", "PATH_DEVICE_FORBIDDEN", "PATH_VOLUME_GUID_FORBIDDEN",
    "PATH_ADS_FORBIDDEN", "PATH_FIXED_VOLUME_REQUIRED", "PATH_REPARSE_FORBIDDEN",
    "PATH_OUTSIDE_ROOT", "PATH_HANDLE_OPEN_FAILED", "PATH_FINAL_QUERY_FAILED",
    "ACL_COMMAND_FAILED", "ACL_OWNER_ONLY_REQUIRED",
]


@final
class PathSecurityError(OSError):
    """Stable path-security failure without retaining the rejected path."""

    def __init__(self, code: PathSecurityCode, operation: str) -> None:
        """Create a redacted error identified only by code and operation."""
        super().__init__(code, operation)
        self.code = code
        self.operation = operation

    @override
    def __str__(self) -> str:
        return f"{self.code}: operation={self.operation}"


@dataclass(frozen=True, slots=True)
class DataRootPaths:
    """Fixed protected storage layout rooted on one local volume."""

    root: Path
    data: Path
    logs: Path
    spool: Path
    tmp: Path
    incoming: Path
    pending: Path
    pending_identity: Path
    pending_dependency: Path
    dead_letter: Path
    archive: Path
    admission_lock: Path

    def directories(self) -> tuple[Path, ...]:
        """Return every directory that must be secured before storage starts."""
        return (
            self.root,
            self.data,
            self.logs,
            self.spool,
            self.tmp,
            self.incoming,
            self.pending,
            self.pending_identity,
            self.pending_dependency,
            self.dead_letter,
            self.archive,
        )


def parse_local_fixed_path(raw: str | Path) -> Path:
    """Parse an absolute, local, fixed-volume path without creating it."""
    if os.name != "nt":
        raise PathSecurityError(code="WINDOWS_REQUIRED", operation="parse")
    expanded = os.path.expandvars(str(raw))
    if _UNRESOLVED_ENV.search(expanded) is not None:
        raise PathSecurityError(code="PATH_UNRESOLVED_ENV", operation="parse")
    lowered = expanded.casefold().replace("/", "\\")
    if lowered.startswith("\\\\?\\volume{"):
        raise PathSecurityError(code="PATH_VOLUME_GUID_FORBIDDEN", operation="parse")
    if lowered.startswith(("\\\\?\\", "\\\\.\\", "\\??\\")):
        raise PathSecurityError(code="PATH_DEVICE_FORBIDDEN", operation="parse")
    if lowered.startswith("\\\\"):
        raise PathSecurityError(code="PATH_UNC_FORBIDDEN", operation="parse")
    drive, tail = ntpath.splitdrive(expanded)
    if not drive or not tail.startswith(("\\", "/")):
        raise PathSecurityError(code="PATH_NOT_ABSOLUTE", operation="parse")
    if ":" in tail:
        raise PathSecurityError(code="PATH_ADS_FORBIDDEN", operation="parse")
    drive_root = f"{drive}\\"
    if ctypes.windll.kernel32.GetDriveTypeW(drive_root) != _DRIVE_FIXED:
        raise PathSecurityError(code="PATH_FIXED_VOLUME_REQUIRED", operation="parse")
    return Path(ntpath.normpath(expanded))


def _assert_reparse_free(path: Path) -> None:
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if not os.path.lexists(current):
            continue
        attributes = current.stat(follow_symlinks=False).st_file_attributes
        if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise PathSecurityError(code="PATH_REPARSE_FORBIDDEN", operation="inspect")


def _final_path_from_handle(path: Path) -> Path:
    flags = native.FILE_FLAG_BACKUP_SEMANTICS if path.is_dir() else 0
    raw_handle = native.create_file(
        native.CREATE_FILE,
        str(path),
        native.FILE_READ_ATTRIBUTES,
        native.OPEN_EXISTING,
        flags,
    )
    if raw_handle == native.INVALID_HANDLE_VALUE:
        raise PathSecurityError(code="PATH_HANDLE_OPEN_FAILED", operation="handle-open")
    handle = native.WinHandle(raw_handle)
    try:
        try:
            return verify_handle(handle, path.resolve(strict=True))
        except native.Win32HandleError as error:
            raise PathSecurityError(
                code="PATH_FINAL_QUERY_FAILED",
                operation="handle-query",
            ) from error
    finally:
        _ = native.close_native(native.CLOSE_HANDLE, handle)


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        return ntpath.commonpath((str(candidate), str(root))).casefold() == str(root).casefold()
    except ValueError:
        return False


def validate_secure_path(path: Path, approved_root: Path) -> Path:
    """Verify lexical, reparse, handle-final, and owner-only ACL containment."""
    candidate = parse_local_fixed_path(path)
    root = parse_local_fixed_path(approved_root)
    if not _is_within(candidate, root):
        raise PathSecurityError(code="PATH_OUTSIDE_ROOT", operation="lexical-containment")
    _assert_reparse_free(candidate)
    final_root = _final_path_from_handle(root)
    final_candidate = _final_path_from_handle(candidate)
    if not _is_within(final_candidate, final_root):
        raise PathSecurityError(code="PATH_OUTSIDE_ROOT", operation="handle-containment")
    acl = inspect_owner_only_acl(candidate)
    if not (
        acl.protected
        and acl.owner_is_current
        and acl.ace_count == 1
        and acl.sole_ace_is_current_full_control
    ):
        raise PathSecurityError(code="ACL_OWNER_ONLY_REQUIRED", operation="acl-validation")
    return final_candidate


def secure_owner_only_file(
    path: Path,
    approved_root: Path,
    *,
    create: bool,
) -> Path:
    """Create when requested, then protect and validate one exact regular file."""
    candidate = parse_local_fixed_path(path)
    root = parse_local_fixed_path(approved_root)
    if not _is_within(candidate, root):
        raise PathSecurityError(code="PATH_OUTSIDE_ROOT", operation="file-containment")
    _assert_reparse_free(candidate.parent)
    if os.path.lexists(candidate):
        _assert_reparse_free(candidate)
        if not candidate.is_file():
            raise PathSecurityError(code="PATH_HANDLE_OPEN_FAILED", operation="file-type")
    elif create:
        try:
            candidate.touch(exist_ok=False)
        except OSError as error:
            raise PathSecurityError(
                code="PATH_HANDLE_OPEN_FAILED",
                operation="file-create",
            ) from error
    else:
        raise PathSecurityError(code="PATH_HANDLE_OPEN_FAILED", operation="file-open")
    apply_owner_only_acl(candidate, directory=False)
    return validate_secure_path(candidate, root)


class SqliteAclGuard:
    """Track exact SQLite file identities so each sidecar lifecycle is protected once."""

    def __init__(self, path: Path) -> None:
        """Bind the mutable identity cache to one configured database path."""
        self._path: Path = path
        self._secured_identities: dict[Path, tuple[int, int]] = {}

    def secure_present(self, *, create_database: bool) -> None:
        """Protect the database and every WAL/SHM identity currently present."""
        try:
            self._secure_file(self._path, create=create_database)
            for suffix in ("-wal", "-shm"):
                sidecar = self._path.with_name(f"{self._path.name}{suffix}")
                if sidecar.exists():
                    self._secure_file(sidecar, create=False)
        except OSError as error:
            message = "DATABASE_FILE_SECURITY_FAILED"
            raise sqlite3.OperationalError(message) from error

    def _secure_file(self, path: Path, *, create: bool) -> None:
        if path.exists():
            identity = path.stat()
            if self._secured_identities.get(path) == (identity.st_dev, identity.st_ino):
                return
        secured = secure_owner_only_file(path, self._path.parent, create=create)
        identity = secured.stat()
        self._secured_identities[path] = (identity.st_dev, identity.st_ino)


def data_root_paths(raw_root: str | Path) -> DataRootPaths:
    """Build the fixed storage layout without creating or trusting its paths."""
    root = parse_local_fixed_path(raw_root)
    return DataRootPaths(
        root=root,
        data=root / "data",
        logs=root / "logs",
        spool=root / "spool",
        tmp=root / "spool" / "tmp",
        incoming=root / "spool" / "incoming",
        pending=root / "spool" / "pending",
        pending_identity=root / "spool" / "pending" / "identity",
        pending_dependency=root / "spool" / "pending" / "dependency",
        dead_letter=root / "spool" / "dead-letter",
        archive=root / "spool" / "archive",
        admission_lock=root / "spool" / "admission.lock",
    )


def initialize_data_root(raw_root: str | Path) -> DataRootPaths:
    """Create and secure the complete storage layout before returning it for use."""
    paths = data_root_paths(raw_root)
    root = paths.root
    _assert_reparse_free(root)
    root.mkdir(exist_ok=True)
    apply_owner_only_acl(root, directory=True)
    paths = data_root_paths(validate_secure_path(root, root))
    for directory in paths.directories()[1:]:
        directory.mkdir(exist_ok=True)
        apply_owner_only_acl(directory, directory=True)
        _ = validate_secure_path(directory, paths.root)
    if not paths.admission_lock.exists():
        paths.admission_lock.touch(exist_ok=False)
    apply_owner_only_acl(paths.admission_lock, directory=False)
    if paths.admission_lock.stat().st_size == 0:
        with paths.admission_lock.open("wb") as lock_stream:
            _ = lock_stream.write(b"\0")
            lock_stream.flush()
            os.fsync(lock_stream.fileno())
    _ = validate_secure_path(paths.admission_lock, paths.root)
    return paths
