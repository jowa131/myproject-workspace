"""Cross-process Windows spool admission lock."""

import errno
import msvcrt
from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep
from types import TracebackType
from typing import BinaryIO, Self, final, override

from codex_ticket_dashboard.storage.win32_acl import apply_acl, inspect_acl


@dataclass(frozen=True, slots=True)
class AclInspection:
    """Privacy-safe binary owner-only ACL observables."""

    protected: bool
    owner_is_current: bool
    ace_count: int
    sole_ace_is_current_full_control: bool


@final
class AclCommandError(OSError):
    """Stable ACL command failure without command output or path content."""

    def __init__(self) -> None:
        """Create the fixed ACL failure code."""
        super().__init__("ACL_COMMAND_FAILED")

    @override
    def __str__(self) -> str:
        return "ACL_COMMAND_FAILED"


@final
class AdmissionLockError(OSError):
    """Stable admission-lock failure without a path or accepted identifier."""

    def __init__(self) -> None:
        """Create the fixed admission-lock failure code."""
        super().__init__("ADMISSION_LOCK_FAILED")

    @override
    def __str__(self) -> str:
        return "ADMISSION_LOCK_FAILED"


def apply_owner_only_acl(path: Path, *, directory: bool) -> None:
    """Replace the target DACL with one protected current-user full-control ACE."""
    try:
        apply_acl(path, directory=directory)
    except OSError:
        raise AclCommandError from None


def inspect_owner_only_acl(path: Path) -> AclInspection:
    """Return redacted binary ACL observables for an existing path."""
    try:
        return AclInspection(*inspect_acl(path))
    except OSError:
        raise AclCommandError from None


@final
class AdmissionLock:
    """Own one byte-range lock for the no-clobber decision and replace."""

    def __init__(self, path: Path) -> None:
        """Bind the lock to its pre-created protected file."""
        self._path: Path = path
        self._file: BinaryIO | None = None

    def __enter__(self) -> Self:
        """Acquire the one-byte lock within a fixed 250ms contention budget."""
        file = self._path.open("r+b", buffering=0)
        _ = file.seek(0)
        try:
            deadline = monotonic() + 0.25
            while True:
                try:
                    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as error:
                    remaining = deadline - monotonic()
                    if error.errno != errno.EACCES or remaining <= 0:
                        raise
                    sleep(min(0.01, remaining))
                    if monotonic() >= deadline:
                        raise
        except OSError as error:
            file.close()
            raise AdmissionLockError from error
        self._file = file
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release and close the lock file regardless of body outcome."""
        file = self._file
        if file is None:
            return
        _ = file.seek(0)
        msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
        file.close()
        self._file = None
