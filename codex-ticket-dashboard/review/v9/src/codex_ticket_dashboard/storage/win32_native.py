# ruff: noqa: D101, D103 -- declarations are documented by the typed handle layer.
"""Strict ctypes ABI declarations used only by the typed storage handle layer."""

import ctypes
from ctypes import wintypes
from enum import StrEnum, unique
from typing import Final, NewType, Protocol, final

WinHandle = NewType("WinHandle", int)
GENERIC_READ: Final = 0x80000000
GENERIC_WRITE: Final = 0x40000000
DELETE_ACCESS: Final = 0x00010000
FILE_READ_ATTRIBUTES: Final = 0x00000080
OPEN_EXISTING: Final = 3
NT_FILE_CREATE: Final = 2
NT_FILE_OPEN: Final = 1
FILE_FLAG_BACKUP_SEMANTICS: Final = 0x02000000
_SYNCHRONIZE: Final = 0x00100000
_FILE_NON_DIRECTORY_FILE: Final = 0x00000040
_FILE_SYNCHRONOUS_IO_NONALERT: Final = 0x00000020
FILE_SHARE_READ_WRITE: Final = 0x00000003
FILE_SHARE_DELETE: Final = 0x00000004
FILE_FLAG_OPEN_REPARSE_POINT: Final = 0x00200000
FILE_ATTRIBUTE_REPARSE_POINT: Final = 0x00000400
FILE_ATTRIBUTE_TAG_INFO_CLASS: Final = 9
FILE_RENAME_INFORMATION_CLASS: Final = 10
ERROR_FILE_EXISTS: Final = 80
ERROR_ALREADY_EXISTS: Final = 183
STATUS_OBJECT_NAME_COLLISION: Final = -1_073_741_771
INVALID_HANDLE_VALUE: Final = ctypes.c_void_p(-1).value


@unique
class Win32HandleCode(StrEnum):
    """Stable native failure classes used by the spool boundary."""

    OPEN_FAILED = "OPEN_FAILED"
    FILE_EXISTS = "FILE_EXISTS"
    FINAL_PATH_FAILED = "FINAL_PATH_FAILED"
    PATH_MISMATCH = "PATH_MISMATCH"
    REPARSE_FORBIDDEN = "REPARSE_FORBIDDEN"
    RENAME_FAILED = "RENAME_FAILED"


@final
class Win32HandleError(OSError):
    """Redacted native-handle failure with no path or payload content."""

    def __init__(self, code: Win32HandleCode, native_code: int | None = None) -> None:
        """Create one stable native failure."""
        super().__init__(code.value)
        self.code = code
        self.native_code = native_code


class _CreateFile(Protocol):
    def __call__(  # noqa: PLR0913, PLR0917 -- exact Win32 ABI signature.
        self,
        name: str,
        access: int,
        share: int,
        security: int | None,
        creation: int,
        flags: int,
        template: int | None,
    ) -> int: ...


class _GetFinalPath(Protocol):
    def __call__(
        self,
        handle: int,
        buffer: ctypes.Array[ctypes.c_wchar],
        length: int,
        flags: int,
    ) -> int: ...


class _HandleInformation(Protocol):
    def __call__(self, handle: int, info_class: int, buffer: int, size: int) -> int: ...


class _NtSetInformation(Protocol):
    def __call__(
        self,
        handle: int,
        io_status: int,
        buffer: int,
        size: int,
        info_class: int,
    ) -> int: ...


class _NtCreate(Protocol):
    def __call__(  # noqa: PLR0913, PLR0917 -- exact NT ABI signature.
        self,
        handle: int,
        access: int,
        attributes: int,
        io_status: int,
        allocation_size: int | None,
        file_attributes: int,
        share: int,
        disposition: int,
        options: int,
        extended_attributes: int | None,
        extended_attributes_length: int,
    ) -> int: ...


class _CloseHandle(Protocol):
    def __call__(self, handle: int) -> int: ...


@final
class FileAttributeTagInfo(ctypes.Structure):
    attributes: int = 0
    reparse_tag: int = 0
    _fields_ = (("attributes", wintypes.DWORD), ("reparse_tag", wintypes.DWORD))


@final
class FileRenameInformation(ctypes.Structure):
    _fields_ = (
        ("replace_if_exists", ctypes.c_ubyte),
        ("root_directory", wintypes.HANDLE),
        ("file_name_length", wintypes.DWORD),
        ("file_name", wintypes.WCHAR * 1),
    )


@final
class IoStatusUnion(ctypes.Union):
    _fields_ = (("status", wintypes.LONG), ("pointer", wintypes.LPVOID))


@final
class IoStatusBlock(ctypes.Structure):
    _fields_ = (("result", IoStatusUnion), ("information", ctypes.c_size_t))


@final
class UnicodeString(ctypes.Structure):
    _fields_ = (
        ("length", wintypes.USHORT),
        ("maximum_length", wintypes.USHORT),
        ("buffer", wintypes.LPVOID),
    )


@final
class ObjectAttributes(ctypes.Structure):
    _fields_ = (
        ("length", wintypes.ULONG),
        ("root_directory", wintypes.HANDLE),
        ("object_name", wintypes.LPVOID),
        ("attributes", wintypes.ULONG),
        ("security_descriptor", wintypes.LPVOID),
        ("security_quality_of_service", wintypes.LPVOID),
    )


_KERNEL32: Final = ctypes.WinDLL("kernel32", use_last_error=True)
CREATE_FILE: Final[_CreateFile] = ctypes.WINFUNCTYPE(
    wintypes.HANDLE,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HANDLE,
    use_last_error=True,
)(("CreateFileW", _KERNEL32))
GET_FINAL_PATH: Final[_GetFinalPath] = ctypes.WINFUNCTYPE(
    wintypes.DWORD,
    wintypes.HANDLE,
    wintypes.LPWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    use_last_error=True,
)(("GetFinalPathNameByHandleW", _KERNEL32))
GET_HANDLE_INFO: Final[_HandleInformation] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
    use_last_error=True,
)(("GetFileInformationByHandleEx", _KERNEL32))
_NTDLL: Final = ctypes.WinDLL("ntdll", use_last_error=True)
NT_SET_INFORMATION: Final[_NtSetInformation] = ctypes.WINFUNCTYPE(
    wintypes.LONG,
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.c_int,
)(("NtSetInformationFile", _NTDLL))
NT_CREATE: Final[_NtCreate] = ctypes.WINFUNCTYPE(
    wintypes.LONG,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
)(("NtCreateFile", _NTDLL))
CLOSE_HANDLE: Final[_CloseHandle] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
)(("CloseHandle", _KERNEL32))


def get_handle_info(
    function: _HandleInformation,
    handle: WinHandle,
    info_class: int,
    buffer: int,
    size: int,
) -> int:
    return function(handle, info_class, buffer, size)


def get_final_path(
    function: _GetFinalPath,
    handle: WinHandle,
    buffer: ctypes.Array[ctypes.c_wchar],
    length: int,
) -> int:
    return function(handle, buffer, length, 0)


def create_file(
    function: _CreateFile,
    path: str,
    access: int,
    creation: int,
    flags: int,
) -> int:
    return function(
        path,
        access,
        FILE_SHARE_READ_WRITE,
        None,
        creation,
        flags | FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )


def close_native(function: _CloseHandle, handle: WinHandle) -> int:
    return function(handle)


def rename_native(
    function: _NtSetInformation,
    handle: WinHandle,
    io_status: int,
    buffer: int,
    size: int,
) -> int:
    return function(handle, io_status, buffer, size, FILE_RENAME_INFORMATION_CLASS)


def create_relative_native(  # noqa: PLR0913, PLR0917 -- typed NT ABI adapter.
    function: _NtCreate,
    handle_pointer: int,
    access: int,
    attributes_pointer: int,
    io_status_pointer: int,
    disposition: int,
    share: int,
) -> int:
    return function(
        handle_pointer,
        access | _SYNCHRONIZE,
        attributes_pointer,
        io_status_pointer,
        None,
        0,
        share,
        disposition,
        _FILE_NON_DIRECTORY_FILE | _FILE_SYNCHRONOUS_IO_NONALERT,
        None,
        0,
    )
