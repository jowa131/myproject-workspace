"""Bounded latest lifecycle command results without Hook content."""

from __future__ import annotations

import ctypes
import msvcrt
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Annotated, ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

import codex_ticket_dashboard.storage.win32_native as native
from codex_ticket_dashboard.lifecycle.contracts import MetadataId, logical_thread_id
from codex_ticket_dashboard.storage.path_security import (
    DataRootPaths,
    secure_owner_only_file,
    validate_secure_path,
)
from codex_ticket_dashboard.storage.win32_handles import (
    VerifiedHandle,
    create_pinned_binary,
    verify_handle,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

type DiagnosticHook = Literal[
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "SessionEnd",
    "UNKNOWN",
]
type DiagnosticStatus = Literal["STARTED", "SUCCEEDED", "FAILED"]
type ProcessingStage = Literal["NORMALIZATION", "IDENTITY", "ADMISSION"]
type ResultCode = Literal[
    "PENDING",
    "RECORDED",
    "INPUT_INVALID",
    "INPUT_TOO_LARGE",
    "PATH_INVALID",
    "CONFIG_INVALID",
    "STORAGE_UNAVAILABLE",
    "IDEMPOTENCY_PAYLOAD_COLLISION",
    "ADMISSION_UNVERIFIED",
    "OBSERVER_INTERNAL_ERROR",
]
_MAX_BYTES: Final = 2_048


class _HookKey(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore", strict=True, hide_input_in_errors=True
    )
    hook_event_name: DiagnosticHook


class _ThreadKey(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore", strict=True, hide_input_in_errors=True
    )
    session_id: MetadataId
    agent_id: MetadataId | None = None


class _TurnKey(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="ignore", strict=True, hide_input_in_errors=True
    )
    turn_id: MetadataId | None = None


class _CommandDiagnostic(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    hook_event: DiagnosticHook
    status: DiagnosticStatus
    stage: ProcessingStage
    code: ResultCode
    thread_id: Annotated[str, Field(pattern=r"^thr_[A-Za-z0-9_-]{1,128}$")] | None
    turn_id: MetadataId | None


class _DiagnosticContext(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid", strict=True)
    hook_event: DiagnosticHook
    thread_id: Annotated[str, Field(pattern=r"^thr_[A-Za-z0-9_-]{1,128}$")] | None
    turn_id: MetadataId | None


def parse_diagnostic_context(raw: bytes) -> _DiagnosticContext:
    """Extract only closed routing metadata, independently omitting invalid identifiers."""
    try:
        hook = _HookKey.model_validate_json(raw).hook_event_name
    except ValidationError:
        hook = "UNKNOWN"
    try:
        thread = _ThreadKey.model_validate_json(raw)
        thread_id = logical_thread_id(thread.agent_id or thread.session_id)
    except ValidationError:
        thread_id = None
    try:
        turn_id = _TurnKey.model_validate_json(raw).turn_id
    except ValidationError:
        turn_id = None
    return _DiagnosticContext(hook_event=hook, thread_id=thread_id, turn_id=turn_id)


def publish_command_diagnostic(
    paths: DataRootPaths,
    context: _DiagnosticContext,
    result: tuple[DiagnosticStatus, ProcessingStage, ResultCode],
) -> None:
    """Best-effort publish; diagnostic failure never changes observation authority."""
    try:
        status, stage, code = result
        snapshot = _CommandDiagnostic(
            hook_event=context.hook_event,
            status=status,
            stage=stage,
            code=code,
            thread_id=context.thread_id,
            turn_id=context.turn_id,
        )
        _write_snapshot(paths, snapshot)
    except Exception:  # noqa: BLE001 -- diagnostics must not alter Hook behavior.
        return


@contextmanager
def _pin_directory(path: Path, root: Path) -> Generator[VerifiedHandle]:
    canonical = validate_secure_path(path, root)
    value = native.create_file(
        native.CREATE_FILE,
        str(canonical),
        native.FILE_READ_ATTRIBUTES,
        native.OPEN_EXISTING,
        native.FILE_FLAG_BACKUP_SEMANTICS | native.FILE_FLAG_OPEN_REPARSE_POINT,
    )
    if value == native.INVALID_HANDLE_VALUE:
        raise OSError
    handle = native.WinHandle(value)
    try:
        yield VerifiedHandle(handle, verify_handle(handle, canonical))
    finally:
        _ = native.close_native(native.CLOSE_HANDLE, handle)


def _write_snapshot(paths: DataRootPaths, state: _CommandDiagnostic) -> None:
    payload = state.model_dump_json().encode()
    if len(payload) > _MAX_BYTES or paths.logs != paths.root / "logs":
        raise OSError
    name = f"lifecycle-command-{state.hook_event}.json"
    with (
        _pin_directory(paths.root, paths.root) as root,
        _pin_directory(root.final_path / "logs", root.final_path) as logs,
    ):
        temporary = logs.final_path / f"{name}.{os.getpid()}.tmp"
        created = False
        try:
            with create_pinned_binary(temporary, logs) as opened:
                created = True
                _ = secure_owner_only_file(temporary, root.final_path, create=False)
                _ = opened.stream.write(payload)
                os.fsync(opened.stream.fileno())
                _replace(
                    native.WinHandle(msvcrt.get_osfhandle(opened.stream.fileno())),
                    logs,
                    name,
                )
        finally:
            if created:
                temporary.unlink(missing_ok=True)


def _replace(handle: native.WinHandle, parent: VerifiedHandle, name: str) -> None:
    encoded = name.encode("utf-16-le")
    offset = native.FileRenameInformation.file_name.offset
    buffer = ctypes.create_string_buffer(offset + len(encoded))
    info = native.FileRenameInformation.from_buffer(buffer)
    info.replace_if_exists = True
    info.root_directory = parent.value
    info.file_name_length = len(encoded)
    _ = ctypes.memmove(ctypes.addressof(buffer) + offset, encoded, len(encoded))
    io = native.IoStatusBlock()
    status = native.rename_native(
        native.NT_SET_INFORMATION,
        handle,
        ctypes.addressof(io),
        ctypes.addressof(buffer),
        len(buffer),
    )
    if status < 0:
        raise OSError
    _ = verify_handle(handle, parent.final_path / name)
