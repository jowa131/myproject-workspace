"""Per-call owner-only ACL operations with verified handles and owned native memory."""

import ctypes
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import final

import codex_ticket_dashboard.storage.win32_acl_native as security
import codex_ticket_dashboard.storage.win32_native as files
from codex_ticket_dashboard.storage.win32_handles import verify_handle


@final
class NativeAclError(OSError):
    """Fixed internal failure; callers expose only their established ACL error."""

    def __init__(self) -> None:
        """Do not retain native path or security descriptor data in errors."""
        super().__init__("ACL_COMMAND_FAILED")


def _require(succeeded: int) -> None:
    if succeeded == 0:
        raise NativeAclError


@contextmanager
def _current_sid() -> Generator[int]:
    token = ctypes.c_void_p()
    opened = security.OPEN_THREAD_TOKEN(
        security.GET_CURRENT_THREAD(),
        security.TOKEN_QUERY,
        1,
        ctypes.addressof(token),
    )
    if opened == 0:
        if ctypes.get_last_error() != security.ERROR_NO_TOKEN:
            raise NativeAclError
        _require(
            security.OPEN_PROCESS_TOKEN(
                security.GET_CURRENT_PROCESS(),
                security.TOKEN_QUERY,
                ctypes.addressof(token),
            )
        )
    handle = token.value
    if handle is None:
        raise NativeAclError
    try:
        needed = ctypes.c_ulong()
        result = security.GET_TOKEN_INFORMATION(
            handle,
            security.TOKEN_USER,
            None,
            0,
            ctypes.addressof(needed),
        )
        if result != 0 or ctypes.get_last_error() != security.ERROR_INSUFFICIENT_BUFFER:
            raise NativeAclError
        buffer = ctypes.create_string_buffer(needed.value)
        _require(
            security.GET_TOKEN_INFORMATION(
                handle,
                security.TOKEN_USER,
                ctypes.addressof(buffer),
                len(buffer),
                ctypes.addressof(needed),
            )
        )
        sid = ctypes.c_void_p.from_buffer(buffer).value
        if sid is None:
            raise NativeAclError
        _require(security.IS_VALID_SID(sid))
        yield sid
    finally:
        _require(files.CLOSE_HANDLE(handle))


@contextmanager
def _file_handle(path: Path, *, writable: bool) -> Generator[int]:
    access = security.READ_CONTROL | files.FILE_READ_ATTRIBUTES
    if writable:
        access |= security.WRITE_DAC | security.WRITE_OWNER
    handle = files.CREATE_FILE(
        str(path),
        access,
        files.FILE_SHARE_READ_WRITE | files.FILE_SHARE_DELETE,
        None,
        files.OPEN_EXISTING,
        files.FILE_FLAG_BACKUP_SEMANTICS | files.FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == files.INVALID_HANDLE_VALUE:
        raise NativeAclError
    try:
        _ = verify_handle(files.WinHandle(handle), path.resolve(strict=True))
        yield handle
    finally:
        _require(files.CLOSE_HANDLE(handle))


def apply_acl(path: Path, *, directory: bool) -> None:
    """Replace owner and DACL atomically on the verified object, never a null DACL."""
    with _file_handle(path, writable=True) as handle, _current_sid() as sid:
        # ACL header + ACE header/mask + variable SID (all DWORD-aligned).
        acl = ctypes.create_string_buffer(16 + security.GET_LENGTH_SID(sid))
        pointer = ctypes.addressof(acl)
        _require(security.INITIALIZE_ACL(pointer, len(acl), security.ACL_REVISION))
        _require(
            security.ADD_ALLOWED_ACE(
                pointer,
                security.ACL_REVISION,
                3 if directory else 0,
                security.FILE_ALL_ACCESS,
                sid,
            )
        )
        status = security.SET_SECURITY_INFO(
            handle,
            security.SE_FILE_OBJECT,
            security.OWNER_AND_DACL | security.PROTECTED_DACL,
            sid,
            None,
            pointer,
            None,
        )
        if status != 0:
            raise NativeAclError


def _sole_full_control(acl: int, sid: int, *, directory: bool) -> bool:
    pointer = ctypes.c_void_p()
    _require(security.GET_ACE(acl, 0, ctypes.addressof(pointer)))
    ace = pointer.value
    if ace is None:
        raise NativeAclError
    # ACCESS_ALLOWED_ACE begins with type/flags/size, then mask and inline SID.
    header = ctypes.string_at(ace, 8)
    valid_flags = (0, 3) if directory else (0,)
    if header[0] != 0 or header[1] not in valid_flags:
        return False
    if int.from_bytes(header[2:4], "little") < 8 + security.GET_LENGTH_SID(sid):
        return False
    mask = int.from_bytes(header[4:8], "little")
    return (
        mask & security.FILE_ALL_ACCESS == security.FILE_ALL_ACCESS
        and security.IS_VALID_SID(ace + 8) != 0
        and security.EQUAL_SID(ace + 8, sid) != 0
    )


def inspect_acl(path: Path) -> tuple[bool, bool, int, bool]:
    """Read a fresh protected DACL and owner; native allocation lives through inspection."""
    with _file_handle(path, writable=False) as handle, _current_sid() as sid:
        owner, acl, descriptor = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
        status = security.GET_SECURITY_INFO(
            handle,
            security.SE_FILE_OBJECT,
            security.OWNER_AND_DACL,
            ctypes.addressof(owner),
            None,
            ctypes.addressof(acl),
            None,
            ctypes.addressof(descriptor),
        )
        if status != 0:
            raise NativeAclError
        allocation = descriptor.value
        if allocation is None:
            raise NativeAclError
        try:
            control, revision = ctypes.c_ushort(), ctypes.c_ulong()
            _require(
                security.GET_DESCRIPTOR_CONTROL(
                    allocation,
                    ctypes.addressof(control),
                    ctypes.addressof(revision),
                )
            )
            owner_sid, dacl = owner.value, acl.value
            count = 0
            sole = False
            if dacl is not None:
                _require(security.IS_VALID_ACL(dacl))
                count = ctypes.c_ushort.from_address(dacl + 4).value
                if count == 1:
                    sole = _sole_full_control(dacl, sid, directory=path.is_dir())
            return (
                bool(control.value & security.SE_DACL_PROTECTED),
                owner_sid is not None and security.EQUAL_SID(owner_sid, sid) != 0,
                count,
                sole,
            )
        finally:
            if security.LOCAL_FREE(allocation) is not None:
                raise NativeAclError
