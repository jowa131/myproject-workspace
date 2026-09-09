"""Handle-bound terminal disposal for privacy-rejected spool sources."""

import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Final, Literal, Protocol, final, override

import codex_ticket_dashboard.storage.win32_native as native
from codex_ticket_dashboard.storage.path_security import DataRootPaths
from codex_ticket_dashboard.storage.win32_handles import verify_handle

_FILE_DISPOSITION_INFO_CLASS: Final = 4


class _SetFileInformation(Protocol):
    def __call__(
        self,
        handle: int,
        info_class: int,
        buffer: int,
        size: int,
    ) -> int: ...


class _GetLongPathName(Protocol):
    def __call__(
        self,
        short_path: str,
        buffer: ctypes.Array[ctypes.c_wchar],
        length: int,
    ) -> int: ...


@final
class _FileDispositionInfo(ctypes.Structure):
    _fields_ = (("delete_file", wintypes.BOOL),)


_KERNEL32: Final = ctypes.WinDLL("kernel32", use_last_error=True)
_SET_FILE_INFORMATION: Final[_SetFileInformation] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
    use_last_error=True,
)(("SetFileInformationByHandle", _KERNEL32))
_GET_LONG_PATH_NAME: Final[_GetLongPathName] = ctypes.WINFUNCTYPE(
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    wintypes.DWORD,
    use_last_error=True,
)(("GetLongPathNameW", _KERNEL32))


def _set_file_information(
    function: _SetFileInformation,
    handle: native.WinHandle,
    disposition: _FileDispositionInfo,
) -> int:
    return function(
        handle,
        _FILE_DISPOSITION_INFO_CLASS,
        ctypes.addressof(disposition),
        ctypes.sizeof(disposition),
    )


def _get_long_path_name(
    function: _GetLongPathName,
    path: Path,
    buffer: ctypes.Array[ctypes.c_wchar],
) -> int:
    return function(str(path), buffer, len(buffer))


@final
class PrivacyDispositionError(OSError):
    """Fail closed without retaining a rejected path or payload value."""

    code: Literal["PRIVACY_DISPOSITION_FAILED"] = "PRIVACY_DISPOSITION_FAILED"

    def __init__(self, operation: str) -> None:
        """Create one redacted terminal-disposition failure."""
        super().__init__(self.code, operation)
        self.operation = operation

    @override
    def __str__(self) -> str:
        return f"{self.code}: operation={self.operation}"


def _canonical_expected_path(path: Path) -> Path:
    buffer = ctypes.create_unicode_buffer(32_768)
    length = _get_long_path_name(_GET_LONG_PATH_NAME, path, buffer)
    if length == 0 or length >= len(buffer):
        raise PrivacyDispositionError(operation="canonicalize")
    return Path(ctypes.wstring_at(ctypes.addressof(buffer), length))


def dispose_privacy_source(path: Path, paths: DataRootPaths) -> None:
    """Delete one exact scanned source through a verified non-reparse handle."""
    allowed_parents = (
        paths.incoming,
        paths.pending_identity,
        paths.pending_dependency,
    )
    if path.parent not in allowed_parents or path.name != Path(path.name).name:
        raise PrivacyDispositionError(operation="inventory")
    expected_path = _canonical_expected_path(path)
    raw_handle = native.create_file(
        native.CREATE_FILE,
        str(path),
        native.DELETE_ACCESS | native.FILE_READ_ATTRIBUTES,
        native.OPEN_EXISTING,
        0,
    )
    if raw_handle == native.INVALID_HANDLE_VALUE:
        raise PrivacyDispositionError(operation="open")
    handle = native.WinHandle(raw_handle)
    try:
        try:
            _ = verify_handle(handle, expected_path)
        except native.Win32HandleError as error:
            raise PrivacyDispositionError(operation="identity") from error
        disposition = _FileDispositionInfo(delete_file=True)
        deleted = _set_file_information(_SET_FILE_INFORMATION, handle, disposition)
        if deleted == 0:
            raise PrivacyDispositionError(operation="delete")
    finally:
        _ = native.close_native(native.CLOSE_HANDLE, handle)
