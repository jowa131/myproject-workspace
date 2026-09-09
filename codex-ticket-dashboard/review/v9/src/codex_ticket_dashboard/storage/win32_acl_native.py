"""Typed Windows security ABI; pointer arguments are scoped by win32_acl."""

import ctypes
from collections.abc import Callable
from ctypes import wintypes
from typing import Final

READ_CONTROL: Final = 0x00020000
WRITE_DAC: Final = 0x00040000
WRITE_OWNER: Final = 0x00080000
FILE_ALL_ACCESS: Final = 0x001F01FF
OWNER_AND_DACL: Final = 0x00000005
PROTECTED_DACL: Final = 0x80000000
SE_DACL_PROTECTED: Final = 0x1000
SE_FILE_OBJECT: Final = 1
ACL_REVISION: Final = 2
TOKEN_QUERY: Final = 0x0008
TOKEN_USER: Final = 1
ERROR_NO_TOKEN: Final = 1008
ERROR_INSUFFICIENT_BUFFER: Final = 122

_ADVAPI: Final = ctypes.WinDLL("advapi32", use_last_error=True)
_KERNEL: Final = ctypes.WinDLL("kernel32", use_last_error=True)

OPEN_THREAD_TOKEN: Final[Callable[[int, int, int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.BOOL,
    wintypes.LPVOID,
    use_last_error=True,
)(("OpenThreadToken", _ADVAPI))
OPEN_PROCESS_TOKEN: Final[Callable[[int, int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPVOID,
    use_last_error=True,
)(("OpenProcessToken", _ADVAPI))
GET_TOKEN_INFORMATION: Final[Callable[[int, int, int | None, int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.LPVOID,
    use_last_error=True,
)(("GetTokenInformation", _ADVAPI))
GET_CURRENT_PROCESS: Final[Callable[[], int]] = ctypes.WINFUNCTYPE(wintypes.HANDLE)(
    ("GetCurrentProcess", _KERNEL),
)
GET_CURRENT_THREAD: Final[Callable[[], int]] = ctypes.WINFUNCTYPE(wintypes.HANDLE)(
    ("GetCurrentThread", _KERNEL),
)
# LocalFree takes a pointer-sized HLOCAL even when the Python caller passes an integer.
LOCAL_FREE: Final[Callable[[int], int | None]] = ctypes.WINFUNCTYPE(
    wintypes.HLOCAL,
    wintypes.HLOCAL,
)(("LocalFree", _KERNEL))
GET_LENGTH_SID: Final[Callable[[int], int]] = ctypes.WINFUNCTYPE(
    wintypes.DWORD,
    wintypes.LPVOID,
)(("GetLengthSid", _ADVAPI))
IS_VALID_SID: Final[Callable[[int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.LPVOID,
)(("IsValidSid", _ADVAPI))
EQUAL_SID: Final[Callable[[int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.LPVOID,
    wintypes.LPVOID,
)(("EqualSid", _ADVAPI))
INITIALIZE_ACL: Final[Callable[[int, int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
)(("InitializeAcl", _ADVAPI))
ADD_ALLOWED_ACE: Final[Callable[[int, int, int, int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPVOID,
)(("AddAccessAllowedAceEx", _ADVAPI))
SET_SECURITY_INFO: Final[Callable[[int, int, int, int, int | None, int, int | None], int]] = (
    ctypes.WINFUNCTYPE(
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
    )(("SetSecurityInfo", _ADVAPI))
)
GET_SECURITY_INFO: Final[Callable[[int, int, int, int, int | None, int, int | None, int], int]] = (
    ctypes.WINFUNCTYPE(
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.LPVOID,
    )(("GetSecurityInfo", _ADVAPI))
)
GET_DESCRIPTOR_CONTROL: Final[Callable[[int, int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.LPVOID,
)(("GetSecurityDescriptorControl", _ADVAPI))
IS_VALID_ACL: Final[Callable[[int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.LPVOID,
)(("IsValidAcl", _ADVAPI))
GET_ACE: Final[Callable[[int, int, int], int]] = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.LPVOID,
)(("GetAce", _ADVAPI))
