"""Memory-only Hook parsing into the closed lifecycle metadata contract."""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, ClassVar, Final, Literal, final, override

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from codex_ticket_dashboard.lifecycle.contracts import (
    HookEvent,
    LifecyclePayload,
    MetadataId,
    logical_thread_id,
)

MAX_INPUT_BYTES: Final = 1_048_576

type SourceKind = Literal["cli", "vscode", "unknown"]
type ObservationCode = Literal[
    "INPUT_INVALID",
    "INPUT_TOO_LARGE",
    "PATH_INVALID",
    "CONFIG_INVALID",
    "STORAGE_UNAVAILABLE",
    "IDEMPOTENCY_PAYLOAD_COLLISION",
    "ADMISSION_UNVERIFIED",
]


@final
class ObservationError(ValueError):
    """Expose only a fixed boundary code; never retain rejected stdin content."""

    def __init__(self, code: ObservationCode) -> None:
        """Allow Python traceback assignment while keeping the public diagnostic fixed."""
        super().__init__(code)
        self.code: ObservationCode = code

    @override
    def __str__(self) -> str:
        return self.code


class HookMetadata(BaseModel):
    """Discard all unlisted raw fields before returning from the input boundary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="ignore",
        strict=True,
        hide_input_in_errors=True,
    )
    session_id: MetadataId
    cwd: Annotated[str, Field(min_length=1, max_length=32_768)]
    hook_event_name: HookEvent
    turn_id: MetadataId | None = None
    agent_id: MetadataId | None = None
    source: Annotated[str, Field(max_length=64)] | None = None
    stop_hook_active: bool | None = None


@dataclass(frozen=True, slots=True)
class NormalizedHook:
    """Hold cwd only for registry lookup, separate from persistable metadata."""

    cwd: str
    payload: LifecyclePayload
    stop_hook_active: bool | None


def normalize_hook(raw: bytes, source_host: str, source_kind: SourceKind) -> NormalizedHook:
    """Normalize verified Host field names without reading or hashing task content."""
    if len(raw) > MAX_INPUT_BYTES:
        raise ObservationError(code="INPUT_TOO_LARGE")
    try:
        metadata = HookMetadata.model_validate_json(raw)
        own_thread = logical_thread_id(metadata.agent_id or metadata.session_id)
        parent = logical_thread_id(metadata.session_id) if metadata.agent_id is not None else None
        source = (
            metadata.source
            if metadata.source in {"startup", "resume", "compact", "clear"}
            else "unknown"
        )
        key = sha256(json.dumps((source,), separators=(",", ":")).encode()).hexdigest()
        payload = LifecyclePayload(
            source_host=source_host,
            source_kind=source_kind,
            hook_event=metadata.hook_event_name,
            source_event_key=key,
            host_session_id=metadata.session_id,
            thread_id=own_thread,
            turn_id=metadata.turn_id,
            parent_thread_id=parent,
            relation_state="UNVERIFIED",
            coverage="OBSERVED" if metadata.turn_id is not None else "UNVERIFIED",
            mcp_readiness="UNVERIFIED",
        )
    except ValidationError:
        raise ObservationError(code="INPUT_INVALID") from None
    return NormalizedHook(metadata.cwd, payload, metadata.stop_hook_active)
