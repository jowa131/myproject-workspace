"""Frozen common event envelope and receipt variants."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, unique
from typing import Annotated, ClassVar, Literal, Self, assert_never, override

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    field_validator,
    model_validator,
)

from codex_ticket_dashboard.domain.identifiers import (
    EventId,
    IdempotencyKey,
    PayloadDigest,
    ProjectId,
    ProjectObservationId,
    RepoKey,
    SessionId,
    TicketId,
    TurnId,
    WorkItemId,
    parse_event_id,
    parse_idempotency_key,
    parse_payload_digest,
    parse_project_id,
    parse_project_observation_id,
    parse_repo_key,
    parse_session_id,
    parse_ticket_id,
    parse_work_item_id,
)
from codex_ticket_dashboard.domain.source_metadata import McpContextWitness, witness_is_absent

ValidatedEventId = Annotated[EventId, AfterValidator(parse_event_id)]
ValidatedTicketId = Annotated[TicketId, AfterValidator(parse_ticket_id)]
ValidatedWorkItemId = Annotated[WorkItemId, AfterValidator(parse_work_item_id)]
ValidatedProjectObservationId = Annotated[
    ProjectObservationId,
    AfterValidator(parse_project_observation_id),
]
ValidatedProjectId = Annotated[ProjectId, AfterValidator(parse_project_id)]
ValidatedRepoKey = Annotated[RepoKey, AfterValidator(parse_repo_key)]
ValidatedSessionId = Annotated[SessionId, AfterValidator(parse_session_id)]
ValidatedIdempotencyKey = Annotated[IdempotencyKey, AfterValidator(parse_idempotency_key)]
ValidatedPayloadDigest = Annotated[PayloadDigest, AfterValidator(parse_payload_digest)]


@unique
class ActorType(StrEnum):
    """Actors permitted by the event contract."""

    USER = "USER"
    CODEX = "CODEX"
    SYSTEM = "SYSTEM"
    OBSERVER = "OBSERVER"
    RECOVERY = "RECOVERY"


@unique
class EventOrigin(StrEnum):
    """Trusted event admission origins."""

    MCP_TOOL = "MCP_TOOL"
    HOOK = "HOOK"
    COLLECTOR = "COLLECTOR"
    APP_SERVER = "APP_SERVER"
    RECOVERY = "RECOVERY"


@unique
class ProjectResolutionState(StrEnum):
    """Registry-only project resolution outcomes."""

    RESOLVED = "RESOLVED"
    UNCLASSIFIED = "UNCLASSIFIED"
    CONFLICT = "CONFLICT"


@unique
class HookAggregateOutcome(StrEnum):
    """Observed aggregate continuation outcomes across coexisting hooks."""

    CONTINUED = "CONTINUED"
    NOT_CONTINUED = "NOT_CONTINUED"
    UNKNOWN = "UNKNOWN"


@unique
class EventType(StrEnum):
    """Event variants defined by the v1.3 design."""

    THREAD_OBSERVED = "THREAD_OBSERVED"
    THREAD_OBSERVATION_ENDED = "THREAD_OBSERVATION_ENDED"
    USER_FEEDBACK_OBSERVED = "USER_FEEDBACK_OBSERVED"
    USER_DECISION_RECORDED = "USER_DECISION_RECORDED"
    TICKET_PREFLIGHT_RECORDED = "TICKET_PREFLIGHT_RECORDED"
    TICKET_CREATED = "TICKET_CREATED"
    TICKET_LINKED_TO_THREAD = "TICKET_LINKED_TO_THREAD"
    WORK_ITEM_CREATED = "WORK_ITEM_CREATED"
    WORK_ITEM_UPDATED = "WORK_ITEM_UPDATED"
    UNCLASSIFIED_ACTIVITY_CREATED = "UNCLASSIFIED_ACTIVITY_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    STATUS_CONFLICT = "STATUS_CONFLICT"
    STATUS_AUTHORITY_REJECTED = "STATUS_AUTHORITY_REJECTED"
    USER_DECISION_REJECTED = "USER_DECISION_REJECTED"
    TURN_RELATION_RECORDED = "TURN_RELATION_RECORDED"
    HOOK_DECISION_RECORDED = "HOOK_DECISION_RECORDED"
    HOOK_AGGREGATE_OUTCOME_OBSERVED = "HOOK_AGGREGATE_OUTCOME_OBSERVED"
    CONTINUATION_LIMIT_REACHED = "CONTINUATION_LIMIT_REACHED"
    IDEMPOTENCY_PAYLOAD_COLLISION = "IDEMPOTENCY_PAYLOAD_COLLISION"
    PROJECT_POLICY_RESOLVED = "PROJECT_POLICY_RESOLVED"
    PROJECT_IDENTITY_CONFLICT = "PROJECT_IDENTITY_CONFLICT"
    PROJECT_IDENTITY_RESOLVED = "PROJECT_IDENTITY_RESOLVED"
    DEPENDENCY_PENDING = "DEPENDENCY_PENDING"
    DEPENDENCY_APPLIED = "DEPENDENCY_APPLIED"
    DEPENDENCY_FAILED = "DEPENDENCY_FAILED"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    POLICY_DRIFT = "POLICY_DRIFT"
    REVIEW_REQUIREMENTS_INVALIDATED = "REVIEW_REQUIREMENTS_INVALIDATED"
    REVIEW_RETRY_READY = "REVIEW_RETRY_READY"
    NO_ACTIVE_WORK_ITEMS = "NO_ACTIVE_WORK_ITEMS"
    TOOL_RECEIPT_MISMATCH = "TOOL_RECEIPT_MISMATCH"
    PLAN_OBSERVED = "PLAN_OBSERVED"
    SUBAGENT_STARTED = "SUBAGENT_STARTED"
    SUBAGENT_STOPPED = "SUBAGENT_STOPPED"
    TURN_SUMMARIZED = "TURN_SUMMARIZED"
    TURN_STOPPED = "TURN_STOPPED"
    GIT_GATE_REPORTED = "GIT_GATE_REPORTED"
    WIKI_GATE_REPORTED = "WIKI_GATE_REPORTED"
    SUMMARY_INCOMPLETE = "SUMMARY_INCOMPLETE"
    COMPLIANCE_INCOMPLETE = "COMPLIANCE_INCOMPLETE"
    INGEST_RECOVERED = "INGEST_RECOVERED"
    INGEST_REJECTED = "INGEST_REJECTED"
    TICKET_REOPENED = "TICKET_REOPENED"
    TICKET_CLOSED = "TICKET_CLOSED"


type EventContractCode = Literal[
    "TIMEZONE_REQUIRED",
    "RESOLVED_PROJECT_ID_REQUIRED",
    "UNRESOLVED_PROJECT_ID_FORBIDDEN",
    "OBSERVER_AUTHORITY_FORBIDDEN",
    "LIFECYCLE_ENVELOPE_MISMATCH",
    "MCP_CONTEXT_MISMATCH",
]


@dataclass(frozen=True, slots=True)
class EventContractError(ValueError):
    """Stable event contract error without payload content."""

    code: EventContractCode
    field_path: str
    issue_count: Literal[1] = 1

    @override
    def __str__(self) -> str:
        """Return only the code and field path."""
        return f"{self.code}: field={self.field_path} count={self.issue_count}"


class EmptyPayload(BaseModel):
    """Typed empty payload for metadata-only events."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class EventEnvelope[PayloadT: BaseModel](BaseModel):
    """Validated envelope shared by spool and persistence boundaries."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )

    schema_version: Literal[1]
    event_id: ValidatedEventId
    event_type: EventType
    occurred_at: datetime
    received_at: datetime | None
    actor_type: ActorType
    origin: EventOrigin
    project_observation_id: ValidatedProjectObservationId
    project_id: ValidatedProjectId | None
    project_resolution_state: ProjectResolutionState
    repo_key: ValidatedRepoKey | None
    session_id: ValidatedSessionId
    turn_id: TurnId | None
    ticket_id: ValidatedTicketId | None
    work_item_id: ValidatedWorkItemId | None
    causation_event_id: ValidatedEventId | None
    depends_on_event_ids: tuple[ValidatedEventId, ...]
    payload: PayloadT
    idempotency_key: ValidatedIdempotencyKey
    payload_digest: ValidatedPayloadDigest
    mcp_context: McpContextWitness | None = Field(default=None, exclude_if=witness_is_absent)

    @field_validator("occurred_at", "received_at", mode="after")
    @classmethod
    def validate_timezone(cls, value: datetime | None) -> datetime | None:
        """Require explicit timezone offsets on persisted timestamps."""
        if value is not None and value.utcoffset() is None:
            raise EventContractError(code="TIMEZONE_REQUIRED", field_path="timestamp")
        return value

    @model_validator(mode="after")
    def validate_observer_admission(self) -> Self:
        """Prevent Hook observers from admitting business decisions or forged tuples."""
        from codex_ticket_dashboard.lifecycle.contracts import (  # noqa: PLC0415
            HOOK_EVENT_TYPES,
            LifecyclePayload,
        )

        if self.mcp_context is not None and (
            self.origin is not EventOrigin.MCP_TOOL
            or self.session_id != self.mcp_context.thread_id
            or self.turn_id != self.mcp_context.turn_id
        ):
            raise EventContractError(code="MCP_CONTEXT_MISMATCH", field_path="mcp_context")
        adapter: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
        raw_payload = adapter.validate_python(self.payload.model_dump(mode="json"))
        observer_tags = {
            EventType.THREAD_OBSERVED,
            EventType.THREAD_OBSERVATION_ENDED,
            EventType.USER_FEEDBACK_OBSERVED,
            EventType.SUBAGENT_STARTED,
            EventType.SUBAGENT_STOPPED,
            EventType.TURN_STOPPED,
            EventType.HOOK_DECISION_RECORDED,
            EventType.HOOK_AGGREGATE_OUTCOME_OBSERVED,
            EventType.CONTINUATION_LIMIT_REACHED,
            EventType.PLAN_OBSERVED,
            EventType.TOOL_RECEIPT_MISMATCH,
        }
        if self.origin is EventOrigin.HOOK and (
            self.actor_type is not ActorType.OBSERVER
            or self.event_type not in observer_tags
            or not isinstance(raw_payload, dict)
            or raw_payload.get("authority") != "SYSTEM_DERIVED"
        ):
            raise EventContractError(code="OBSERVER_AUTHORITY_FORBIDDEN", field_path="origin")
        payload = (
            LifecyclePayload.model_validate(raw_payload)
            if isinstance(raw_payload, dict) and "lifecycle_version" in raw_payload
            else None
        )
        if payload is not None and (
            self.actor_type is not ActorType.OBSERVER
            or self.origin is not EventOrigin.HOOK
            or self.session_id != payload.thread_id
            or self.turn_id != payload.turn_id
            or self.event_type.value != HOOK_EVENT_TYPES[payload.hook_event]
            or self.ticket_id is not None
            or self.work_item_id is not None
        ):
            raise EventContractError(code="LIFECYCLE_ENVELOPE_MISMATCH", field_path="payload")
        return self

    @model_validator(mode="after")
    def validate_project_resolution(self) -> Self:
        """Keep resolved and unresolved project identity states distinct."""
        match self.project_resolution_state:
            case ProjectResolutionState.RESOLVED:
                if self.project_id is None:
                    raise EventContractError(
                        code="RESOLVED_PROJECT_ID_REQUIRED",
                        field_path="project_id",
                    )
            case ProjectResolutionState.UNCLASSIFIED | ProjectResolutionState.CONFLICT:
                if self.project_id is not None:
                    raise EventContractError(
                        code="UNRESOLVED_PROJECT_ID_FORBIDDEN",
                        field_path="project_id",
                    )
            case unreachable:
                assert_never(unreachable)
        return self
