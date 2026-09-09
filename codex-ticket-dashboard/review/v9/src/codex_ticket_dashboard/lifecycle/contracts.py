"""Metadata-only lifecycle wire contract shared by command and collector."""

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, ClassVar, Final, Literal, Self, override
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from codex_ticket_dashboard.domain.identifiers import (
    IdempotencyKey,
    ProjectObservationId,
    SessionId,
    parse_session_id,
)

MetadataId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
LogicalThreadId = Annotated[str, Field(pattern=r"^thr_[A-Za-z0-9_-]{1,128}$")]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
type CoverageState = Literal["UNVERIFIED", "OBSERVED", "GAP_DETECTED"]
type RelationState = Literal["VERIFIED", "UNVERIFIED", "CONFLICT"]
type StopRequestKind = Literal["TICKET_CORRECTION", "INITIAL_PREFLIGHT"]
type HookEvent = Literal[
    "SessionStart",
    "UserPromptSubmit",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "SessionEnd",
    "PreCompact",
    "PostCompact",
]
type MissingRequirement = Literal[
    "PREFLIGHT",
    "TURN_SUMMARY",
    "GIT_GATE",
    "WIKI_GATE",
    "MCP_UNAVAILABLE",
    "PENDING_INGEST",
    "IDENTITY_UNVERIFIED",
    "POLICY_DECLARATION_MISMATCH",
]

LIFECYCLE_EVENT_TYPES: Final = frozenset(
    {
        "THREAD_OBSERVED",
        "THREAD_OBSERVATION_ENDED",
        "USER_FEEDBACK_OBSERVED",
        "SUBAGENT_STARTED",
        "SUBAGENT_STOPPED",
        "TURN_STOPPED",
    }
)
HOOK_EVENT_TYPES: Final[dict[HookEvent, str]] = {
    "SessionStart": "THREAD_OBSERVED",
    "UserPromptSubmit": "USER_FEEDBACK_OBSERVED",
    "Stop": "TURN_STOPPED",
    "SubagentStart": "SUBAGENT_STARTED",
    "SubagentStop": "SUBAGENT_STOPPED",
    "SessionEnd": "THREAD_OBSERVATION_ENDED",
    "PreCompact": "THREAD_OBSERVED",
    "PostCompact": "THREAD_OBSERVED",
}


@dataclass(frozen=True, slots=True)
class LifecycleContractError(ValueError):
    """Expose a fixed failure code without the rejected metadata."""

    code: Literal["LIFECYCLE_IDENTITY_CONFLICT", "LIFECYCLE_TURN_REQUIRED"]

    @override
    def __str__(self) -> str:
        return self.code


class StopClaim(BaseModel):
    """Single-use durable claim keyed by host, logical thread and original turn."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )
    claim_key: Digest
    original_turn_id: MetadataId
    continuation_turn_id: MetadataId | None = None
    state: Literal["CLAIMED", "CONTINUATION_OBSERVED", "NOT_CONTINUED", "UNVERIFIED"]


class ObserverAuthority(StrEnum):
    """Observation-only authority compatible with the canonical ledger value."""

    SYSTEM_DERIVED = "SYSTEM_DERIVED"


class LifecyclePayload(BaseModel):
    """Closed observation payload; business decisions and free text are absent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )
    authority: Literal[ObserverAuthority.SYSTEM_DERIVED] = ObserverAuthority.SYSTEM_DERIVED
    lifecycle_version: Literal[1] = 1
    source_host: MetadataId
    source_kind: Literal["cli", "vscode", "unknown"]
    hook_event: HookEvent
    source_event_key: MetadataId
    host_session_id: MetadataId
    thread_id: LogicalThreadId
    turn_id: MetadataId | None
    parent_thread_id: LogicalThreadId | None
    relation_state: RelationState
    coverage: CoverageState
    mcp_readiness: Literal["READY", "UNVERIFIED", "UNAVAILABLE"]
    missing_requirements: Annotated[tuple[MissingRequirement, ...], Field(max_length=7)] = ()
    stop_claim: StopClaim | None = None

    @model_validator(mode="after")
    def validate_identity(self) -> Self:
        """Verified child tuples bind Host session to parent, never to parent turn."""
        if self.parent_thread_id == self.thread_id:
            raise LifecycleContractError(code="LIFECYCLE_IDENTITY_CONFLICT")
        if self.relation_state == "VERIFIED":
            expected = self.parent_thread_id or self.thread_id
            if expected != "thr_" + self.host_session_id:
                raise LifecycleContractError(code="LIFECYCLE_IDENTITY_CONFLICT")
        if self.hook_event in {"UserPromptSubmit", "Stop", "SubagentStop"} and self.turn_id is None:
            raise LifecycleContractError(code="LIFECYCLE_TURN_REQUIRED")
        if self.stop_claim is not None and self.hook_event != "Stop":
            raise LifecycleContractError(code="LIFECYCLE_IDENTITY_CONFLICT")
        if self.stop_claim is not None and (
            self.stop_claim.claim_key
            != stop_claim_key(
                self.source_host,
                self.thread_id,
                self.stop_claim.original_turn_id,
            )
            or self.turn_id
            not in {
                self.stop_claim.original_turn_id,
                self.stop_claim.continuation_turn_id,
            }
        ):
            raise LifecycleContractError(code="LIFECYCLE_IDENTITY_CONFLICT")
        return self


class LifecycleRecord(BaseModel):
    """Require the event tag to agree with the typed Hook observation."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )
    event_type: str
    payload: LifecyclePayload

    @model_validator(mode="after")
    def validate_event(self) -> Self:
        """Reject mismatched Hook and ledger event tags before persistence."""
        if self.event_type != HOOK_EVENT_TYPES[self.payload.hook_event]:
            raise LifecycleContractError(code="LIFECYCLE_IDENTITY_CONFLICT")
        return self


def lifecycle_idempotency_key(payload: LifecyclePayload) -> IdempotencyKey:
    """Exclude receipt time and mutable observation claims from source identity."""
    identity = (
        1,
        payload.source_host,
        payload.thread_id,
        payload.turn_id,
        payload.hook_event,
        payload.source_event_key,
    )
    digest = sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()
    return IdempotencyKey("sha256:" + digest)


def stop_claim_key(source_host: str, thread_id: str, original_turn_id: str) -> str:
    """Reuse one durable claim across repeated Stop delivery and continuation."""
    identity = ("stop-claim-v1", source_host, thread_id, original_turn_id)
    return "sha256:" + sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()


def logical_thread_id(raw_id: str) -> SessionId:
    """Prefix an exact Host identifier without guessing a parent or Git identity."""
    adapter: TypeAdapter[str] = TypeAdapter(MetadataId)
    parsed = adapter.validate_python(raw_id)
    return parse_session_id("thr_" + parsed)


def lifecycle_project_observation_id(
    source_host: str,
    thread_id: str,
    path_fingerprint: str,
) -> ProjectObservationId:
    """Create a deterministic UUIDv4-shaped observation ID from nonsecret metadata."""
    identity = ("lifecycle-project-v1", source_host, thread_id, path_fingerprint)
    digest = sha256(json.dumps(identity, separators=(",", ":")).encode()).digest()
    return ProjectObservationId("pobs_" + str(UUID(bytes=digest[:16], version=4)))
