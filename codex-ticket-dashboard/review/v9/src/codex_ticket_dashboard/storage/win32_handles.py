"""Pinned Win32 resource lifetimes for spool mutation operations."""

import ctypes
import msvcrt
import os
import sys
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Protocol

import codex_ticket_dashboard.storage.win32_native as native


@dataclass(frozen=True, slots=True)
class VerifiedHandle:
    """Native handle paired with its verified final path."""

    value: native.WinHandle
    final_path: Path


def verify_handle(handle: native.WinHandle, expected: Path) -> Path:
    """Reject reparse handles and require the exact expected final path."""
    info = native.FileAttributeTagInfo()
    succeeded = native.get_handle_info(
        native.GET_HANDLE_INFO,
        handle,
        native.FILE_ATTRIBUTE_TAG_INFO_CLASS,
        ctypes.addressof(info),
        ctypes.sizeof(info),
    )
    if succeeded == 0:
        raise native.Win32HandleError(native.Win32HandleCode.FINAL_PATH_FAILED)
    if info.attributes & native.FILE_ATTRIBUTE_REPARSE_POINT:
        raise native.Win32HandleError(native.Win32HandleCode.REPARSE_FORBIDDEN)
    buffer = ctypes.create_unicode_buffer(32_768)
    length = native.get_final_path(native.GET_FINAL_PATH, handle, buffer, len(buffer))
    if length == 0 or length >= len(buffer):
        raise native.Win32HandleError(native.Win32HandleCode.FINAL_PATH_FAILED)
    value = ctypes.wstring_at(ctypes.addressof(buffer), length)
    if value.startswith("\\\\?\\UNC\\"):
        raise native.Win32HandleError(native.Win32HandleCode.PATH_MISMATCH)
    final_path = Path(value.removeprefix("\\\\?\\"))
    if final_path != expected:
        raise native.Win32HandleError(native.Win32HandleCode.PATH_MISMATCH)
    return final_path


def _open_verified(
    path: Path,
    expected: Path,
    access: int,
    creation: int,
    flags: int,
) -> VerifiedHandle:
    value = native.create_file(
        native.CREATE_FILE,
        str(path),
        access,
        creation,
        flags,
    )
    if value == native.INVALID_HANDLE_VALUE:
        code = ctypes.get_last_error()
        if code in (native.ERROR_FILE_EXISTS, native.ERROR_ALREADY_EXISTS):
            raise native.Win32HandleError(native.Win32HandleCode.FILE_EXISTS, code)
        raise native.Win32HandleError(native.Win32HandleCode.OPEN_FAILED, code)
    handle = native.WinHandle(value)
    try:
        return VerifiedHandle(handle, verify_handle(handle, expected))
    except native.Win32HandleError:
        _ = native.close_native(native.CLOSE_HANDLE, handle)
        raise


def _open_relative(
    directory: VerifiedHandle,
    file_name: str,
    access: int,
    disposition: int,
    share: int = native.FILE_SHARE_READ_WRITE,
) -> VerifiedHandle:
    if Path(file_name).name != file_name or ":" in file_name:
        raise native.Win32HandleError(native.Win32HandleCode.OPEN_FAILED)
    _ = verify_handle(directory.value, directory.final_path)
    encoded_name = file_name.encode("utf-16-le")
    name_buffer = ctypes.create_unicode_buffer(file_name)
    name = native.UnicodeString(
        len(encoded_name), len(encoded_name) + 2, ctypes.addressof(name_buffer)
    )
    attributes = native.ObjectAttributes(
        ctypes.sizeof(native.ObjectAttributes),
        directory.value,
        ctypes.addressof(name),
        0,
        None,
        None,
    )
    handle_pointer = ctypes.c_void_p()
    io_status = native.IoStatusBlock()
    status = native.create_relative_native(
        native.NT_CREATE,
        ctypes.addressof(handle_pointer),
        access,
        ctypes.addressof(attributes),
        ctypes.addressof(io_status),
        disposition,
        share,
    )
    if status < 0:
        if status == native.STATUS_OBJECT_NAME_COLLISION:
            raise native.Win32HandleError(native.Win32HandleCode.FILE_EXISTS, status)
        raise native.Win32HandleError(native.Win32HandleCode.OPEN_FAILED, status)
    raw = ctypes.string_at(ctypes.addressof(handle_pointer), ctypes.sizeof(handle_pointer))
    handle = native.WinHandle(int.from_bytes(raw, byteorder=sys.byteorder))
    try:
        return VerifiedHandle(handle, verify_handle(handle, directory.final_path / file_name))
    except native.Win32HandleError:
        _ = native.close_native(native.CLOSE_HANDLE, handle)
        raise


def rename_handle(handle: native.WinHandle, directory: VerifiedHandle, file_name: str) -> Path:
    """Rename one retained file handle relative to a retained directory handle."""
    destination = directory.final_path / file_name
    encoded_name = file_name.encode("utf-16-le")
    offset = native.FileRenameInformation.file_name.offset
    buffer = ctypes.create_string_buffer(offset + len(encoded_name))
    info = native.FileRenameInformation.from_buffer(buffer)
    info.replace_if_exists = False
    info.root_directory = directory.value
    info.file_name_length = len(encoded_name)
    _ = ctypes.memmove(ctypes.addressof(buffer) + offset, encoded_name, len(encoded_name))
    io_status = native.IoStatusBlock()
    status = native.rename_native(
        native.NT_SET_INFORMATION,
        handle,
        ctypes.addressof(io_status),
        ctypes.addressof(buffer),
        len(buffer),
    )
    if status < 0:
        raise native.Win32HandleError(native.Win32HandleCode.RENAME_FAILED, status)
    _ = verify_handle(handle, destination)
    return destination


class _SpoolPathLayout(Protocol):
    """Path subset required to pin every spool directory component."""

    @property
    def root(self) -> Path: ...

    @property
    def spool(self) -> Path: ...

    @property
    def tmp(self) -> Path: ...

    @property
    def incoming(self) -> Path: ...


@dataclass(frozen=True, slots=True)
class PinnedSpoolDirectories:
    """Every directory component retained without delete sharing."""

    root: VerifiedHandle
    spool: VerifiedHandle
    tmp: VerifiedHandle
    incoming: VerifiedHandle


@contextmanager
def _pin_directory(
    path: Path,
    expected: Path,
) -> Generator[VerifiedHandle, None, None]:
    handle = _open_verified(
        path,
        expected,
        native.FILE_READ_ATTRIBUTES,
        native.OPEN_EXISTING,
        native.FILE_FLAG_BACKUP_SEMANTICS,
    )
    try:
        yield handle
    finally:
        _ = native.close_native(native.CLOSE_HANDLE, handle.value)


@contextmanager
def pin_spool_directories(
    layout: _SpoolPathLayout,
) -> Generator[PinnedSpoolDirectories, None, None]:
    """Pin and verify root, spool, tmp, and incoming until publication ends."""
    with (
        _pin_directory(layout.root, layout.root) as root,
        _pin_directory(layout.spool, root.final_path / "spool") as spool,
        _pin_directory(layout.tmp, spool.final_path / "tmp") as tmp,
        _pin_directory(layout.incoming, spool.final_path / "incoming") as incoming,
    ):
        yield PinnedSpoolDirectories(root, spool, tmp, incoming)


@dataclass(frozen=True, slots=True)
class PinnedBinaryFile:
    """Actual created file handle retained through fsync and atomic rename."""

    stream: BinaryIO

    def rename_to(self, directory: VerifiedHandle, file_name: str) -> Path:
        """Publish this exact open file handle without destination replacement."""
        descriptor = self.stream.fileno()
        source_identity = os.fstat(descriptor)
        handle = native.WinHandle(msvcrt.get_osfhandle(descriptor))
        destination = rename_handle(handle, directory, file_name)
        destination_file = _open_relative(
            directory,
            file_name,
            native.GENERIC_READ | native.FILE_READ_ATTRIBUTES,
            native.NT_FILE_OPEN,
            native.FILE_SHARE_READ_WRITE | native.FILE_SHARE_DELETE,
        )
        try:
            reopened = msvcrt.open_osfhandle(
                destination_file.value,
                os.O_BINARY | os.O_RDONLY,
            )
        except OSError:
            _ = native.close_native(native.CLOSE_HANDLE, destination_file.value)
            raise
        with os.fdopen(reopened, "rb", buffering=0):
            destination_identity = os.fstat(reopened)
            if (
                destination_identity.st_dev != source_identity.st_dev
                or destination_identity.st_ino != source_identity.st_ino
            ):
                raise native.Win32HandleError(native.Win32HandleCode.PATH_MISMATCH)
        return destination


@contextmanager
def create_pinned_binary(
    path: Path,
    parent: VerifiedHandle,
) -> Generator[PinnedBinaryFile, None, None]:
    """Create and retain a no-clobber temporary file under a pinned parent."""
    native_file = _open_relative(
        parent,
        path.name,
        native.GENERIC_READ
        | native.GENERIC_WRITE
        | native.DELETE_ACCESS
        | native.FILE_READ_ATTRIBUTES,
        native.NT_FILE_CREATE,
    )
    try:
        descriptor = msvcrt.open_osfhandle(native_file.value, os.O_BINARY | os.O_RDWR)
    except OSError:
        _ = native.close_native(native.CLOSE_HANDLE, native_file.value)
        raise
    with os.fdopen(descriptor, "w+b", buffering=0) as stream:
        yield PinnedBinaryFile(stream)


def read_pinned_bytes(path: Path, parent: VerifiedHandle) -> bytes:
    """Read an existing destination through its retained verified handle."""
    native_file = _open_relative(
        parent,
        path.name,
        native.GENERIC_READ | native.FILE_READ_ATTRIBUTES,
        native.NT_FILE_OPEN,
    )
    try:
        descriptor = msvcrt.open_osfhandle(native_file.value, os.O_BINARY | os.O_RDONLY)
    except OSError:
        _ = native.close_native(native.CLOSE_HANDLE, native_file.value)
        raise
    with os.fdopen(descriptor, "rb", buffering=0) as stream:
        return stream.read()
