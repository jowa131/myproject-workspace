"""Bounded diagnostic counters, never business events or admission authority."""

from __future__ import annotations

import ctypes
import msvcrt
import os
from contextlib import asynccontextmanager, contextmanager
from threading import Lock
from typing import TYPE_CHECKING, Annotated, ClassVar, Final, Literal
from uuid import uuid4

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

import codex_ticket_dashboard.storage.win32_native as native
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
    from collections.abc import AsyncGenerator, Generator
    from pathlib import Path

    from mcp.server.mcpserver import MCPServer

type ToolName = Literal[
    "ticket_preflight_record",
    "task_upsert",
    "ticket_status_update",
    "ticket_user_decision_record",
    "ticket_turn_summary",
    "git_gate_report",
    "wiki_update_record",
    "UNKNOWN",
]
type ErrorCode = Literal[
    "INVALID_TOOL_INPUT",
    "OBSERVER_CONTEXT_UNAVAILABLE",
    "OFFICIAL_CONTEXT_INVALID",
    "OFFICIAL_CONTEXT_CONFLICT",
    "OFFICIAL_TURN_MISSING",
    "OBSERVER_CONTEXT_MISSING",
    "OBSERVER_CONTEXT_CONFLICT",
    "PROJECT_IDENTITY_UNVERIFIED",
    "PROJECT_REGISTRY_CONFLICT",
    "MODEL_CONTEXT_CONFLICT",
    "CORRECTION_CAUSE_CONFLICT",
    "POLICY_CONTEXT_UNVERIFIED",
    "PREFLIGHT_POLICY_DECLARATION_MISMATCH",
    "POLICY_DECLARATION_MISMATCH",
    "MODEL_POLICY_CONTEXT_CONFLICT",
    "WIKI_RESULT_MISMATCH",
    "IDEMPOTENCY_PAYLOAD_COLLISION",
]
type ErrorClass = Literal["ToolError", "ValidationError", "OSError", "Exception", "BaseException"]
type Count = Annotated[int, Field(ge=0)]
_TOOL: Final[TypeAdapter[ToolName]] = TypeAdapter(ToolName)
_CODE: Final[TypeAdapter[ErrorCode]] = TypeAdapter(ErrorCode)
_MAX_BYTES: Final = 16_384


class DiagnosticSnapshot(BaseModel):
    """Closed metadata shape; closed and reliable are both required for zero-call evidence."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[1] = 1
    pid: Annotated[int, Field(gt=0)] = Field(default_factory=os.getpid)
    instance_nonce: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")] = Field(
        default_factory=lambda: uuid4().hex
    )
    initialized: bool = True
    closed: bool = False
    reliable: bool = True
    revision: Count = 0
    write_failures: Count = 0
    lifespan_entries: Count = 0
    entered: Count = 0
    official: Count = 0
    bound: Count = 0
    returned: Count = 0
    response_flag_known: Count = 0
    response_is_error: Count = 0
    rejected: Count = 0
    in_flight: Count = 0
    tools: dict[ToolName, Count] = Field(default_factory=dict)
    errors: dict[ErrorCode, Count] = Field(default_factory=dict)
    classes: dict[ErrorClass, Count] = Field(default_factory=dict)


class AdmissionDiagnostics:
    """One process instance owns its snapshot and a lock across each counter publication."""

    def __init__(self, paths: DataRootPaths | None) -> None:
        """Create the initial zero snapshot without making storage failures fatal."""
        self._paths: DataRootPaths | None = paths
        self._state: DiagnosticSnapshot = DiagnosticSnapshot()
        self._lock: Lock = Lock()
        self._persist()

    @contextmanager
    def observe(self, name: str) -> Generator[ToolName]:
        """Observe outcomes without inspecting arguments or changing exceptions."""
        try:
            tool = _TOOL.validate_python(name)
        except ValidationError:
            tool = "UNKNOWN"
        with self._lock:
            if self._state.closed:
                self._state.closed = False
                self._state.reliable = False
            self._state.entered += 1
            self._state.in_flight += 1
            self._state.tools[tool] = self._state.tools.get(tool, 0) + 1
            self._persist()
        try:
            yield tool
        except BaseException as error:
            self._finish(error)
            raise
        else:
            self._finish(None)

    def mark(self, stage: Literal["official", "bound"]) -> None:
        """Count completed identity stages, retaining no identities."""
        with self._lock:
            if stage == "official":
                self._state.official += 1
            else:
                self._state.bound += 1

    def _finish(self, error: BaseException | None) -> None:
        with self._lock:
            self._state.in_flight -= 1
            if error is None:
                self._state.returned += 1
            else:
                self._state.rejected += 1
                key = _error_class(error)
                self._state.classes[key] = self._state.classes.get(key, 0) + 1
                code = _error_code(error)
                if code is not None:
                    self._state.errors[code] = self._state.errors.get(code, 0) + 1
            self._persist()

    def returned_flag(self, is_error: bool | None) -> None:
        """Count only the fixed response flag, never its result body or applied state."""
        with self._lock:
            self._state.response_flag_known += int(is_error is not None)
            self._state.response_is_error += int(is_error is True)

    def close(self) -> None:
        """Only a completed SDK lifespan finalizes a reliable instance observation."""
        with self._lock:
            self._state.closed = True
            self._state.reliable = (
                self._state.reliable
                and self._state.in_flight == 0
                and self._state.lifespan_entries == 1
            )
            self._persist()

    @asynccontextmanager
    async def lifespan(self, _server: MCPServer[None]) -> AsyncGenerator[None]:
        """Tie finalization to the actual MCP transport lifetime."""
        with self._lock:
            self._state.lifespan_entries += 1
            self._state.closed = False
            self._state.reliable = self._state.reliable and self._state.lifespan_entries == 1
            self._persist()
        try:
            yield None
        finally:
            self.close()

    def _persist(self) -> None:
        self._state.revision += 1
        try:
            _write_snapshot(self._paths, self._state)
        except Exception:  # noqa: BLE001 -- diagnostics failure must not alter tool behavior.
            self._state.reliable = False
            self._state.write_failures += 1


def _error_class(error: BaseException) -> ErrorClass:
    if isinstance(error, ValidationError):
        return "ValidationError"
    if isinstance(error, ToolError):
        return "ToolError"
    if isinstance(error, OSError):
        return "OSError"
    return "Exception" if isinstance(error, Exception) else "BaseException"


def _error_code(error: BaseException) -> ErrorCode | None:
    if not isinstance(error, ToolError) or not error.args or not isinstance(error.args[0], str):
        return None
    try:
        return _CODE.validate_python(error.args[0].partition(":")[0])
    except ValidationError:
        return None


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


def _write_snapshot(paths: DataRootPaths | None, state: DiagnosticSnapshot) -> None:
    if paths is None:
        raise OSError
    payload = state.model_dump_json().encode()
    if len(payload) > _MAX_BYTES or paths.logs != paths.root / "logs":
        raise OSError
    name = f"mcp-admission-{state.pid}-{state.instance_nonce}.json"
    with (
        _pin_directory(paths.root, paths.root) as root,
        _pin_directory(
            root.final_path / "logs",
            root.final_path,
        ) as logs,
    ):
        temporary = logs.final_path / (name + ".tmp")
        created = False
        try:
            with create_pinned_binary(temporary, logs) as opened:
                created = True
                _ = secure_owner_only_file(temporary, root.final_path, create=False)
                _ = opened.stream.write(payload)
                os.fsync(opened.stream.fileno())
                _replace(native.WinHandle(msvcrt.get_osfhandle(opened.stream.fileno())), logs, name)
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
