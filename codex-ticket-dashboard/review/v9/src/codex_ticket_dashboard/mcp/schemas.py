"""Typed MCP request and admission-receipt boundary models."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Annotated, ClassVar, Literal, Never, Self, override

from pydantic import BaseModel, ConfigDict, Field, model_validator

from codex_ticket_dashboard.compliance.git_gate import GitGateStatus
from codex_ticket_dashboard.compliance.policy_resolver import GitRequirement, WikiRequirement
from codex_ticket_dashboard.compliance.wiki_gate import WikiGateStatus
from codex_ticket_dashboard.domain.events import (
    ValidatedEventId,
    ValidatedPayloadDigest,
    ValidatedProjectId,
    ValidatedProjectObservationId,
    ValidatedRepoKey,
    ValidatedSessionId,
    ValidatedTicketId,
    ValidatedWorkItemId,
)
from codex_ticket_dashboard.domain.status import TicketStatus, UserDecision, WorkItemStatus
from codex_ticket_dashboard.ingest.payload_models import (
    SafeEventIds,
    SafeItem,
    SafeItems,
    SafeText,
    SafeTurnId,
    SafeWorkItemIds,
)
from codex_ticket_dashboard.ingest.payloads import VerificationPayload

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
GitRevision = Annotated[str, Field(pattern=r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")]
HashMap = Annotated[dict[str, Sha256], Field(max_length=32)]
RequiredItems = Annotated[tuple[SafeItem, ...], Field(min_length=1, max_length=32)]


class BoundaryModel(BaseModel):
    """Reject unknown MCP fields without echoing their values."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", hide_input_in_errors=True
    )


class EventContext(BoundaryModel):
    """Registry-resolved envelope linkage shared by all seven tools."""

    project_observation_id: ValidatedProjectObservationId
    project_id: ValidatedProjectId
    repo_key: ValidatedRepoKey | None
    session_id: ValidatedSessionId
    turn_id: SafeTurnId
    causation_event_id: ValidatedEventId | None = None
    depends_on_event_ids: SafeEventIds = ()

    @model_validator(mode="after")
    def require_unique_dependencies(self) -> Self:
        """Reject duplicate dependency claims at the MCP boundary."""
        if len(self.depends_on_event_ids) != len(set(self.depends_on_event_ids)):
            _reject("DUPLICATE_DEPENDENCY")
        return self


class TicketPreflightRequest(BoundaryModel):
    """Create one ticket or link a thread through one preflight event."""

    context: EventContext
    disposition: Literal["NEW_TICKET", "LINK_EXISTING", "DISCUSSION_LOG"]
    ticket_id: ValidatedTicketId | None = None
    classification: Literal["TASK", "DISCUSSION", "UNCLASSIFIED"]
    goal: SafeText
    non_goals: SafeItems
    acceptance_criteria: RequiredItems
    declared_git_requirement: GitRequirement
    declared_wiki_requirement: WikiRequirement

    @model_validator(mode="after")
    def require_disposition_ticket_shape(self) -> Self:
        """Require an existing ID only for LINK_EXISTING."""
        linked = self.disposition == "LINK_EXISTING"
        discussion = self.disposition == "DISCUSSION_LOG"
        if linked != (self.ticket_id is not None):
            _reject("PREFLIGHT_TICKET_SHAPE")
        if discussion != (self.classification == "DISCUSSION"):
            _reject("PREFLIGHT_CLASSIFICATION_MISMATCH")
        return self


class TaskUpsertRequest(BoundaryModel):
    """Create or update one task or subtask."""

    context: EventContext
    ticket_id: ValidatedTicketId
    work_item_id: ValidatedWorkItemId | None = None
    parent_work_item_id: ValidatedWorkItemId | None = None
    kind: Literal["TASK", "SUBTASK", "UNCLASSIFIED"]
    title: SafeItem
    status: WorkItemStatus
    acceptance_criteria: RequiredItems
    user_decision_event_id: ValidatedEventId | None = None

    @model_validator(mode="after")
    def require_task_shape(self) -> Self:
        """Bind parent and explicit-decision requirements to the requested state."""
        parent_required = self.kind == "SUBTASK"
        if parent_required != (self.parent_work_item_id is not None):
            _reject("WORK_ITEM_PARENT_MISMATCH")
        removing = self.status in {WorkItemStatus.CANCELLED, WorkItemStatus.SUPERSEDED}
        if removing != (self.user_decision_event_id is not None):
            _reject("WORK_ITEM_DECISION_MISMATCH")
        if removing and self.work_item_id is None:
            _reject("WORK_ITEM_REMOVAL_TARGET_REQUIRED")
        if removing and self.user_decision_event_id not in self.context.depends_on_event_ids:
            _reject("WORK_ITEM_DECISION_DEPENDENCY_REQUIRED")
        return self


class TicketStatusUpdateRequest(BoundaryModel):
    """Record one claimed ticket transition for collector validation."""

    context: EventContext
    ticket_id: ValidatedTicketId
    from_status: TicketStatus
    to_status: TicketStatus
    authority: Literal["CODEX_EXECUTION", "CODEX_RESULT", "USER_EXPLICIT"]
    user_decision_event_id: ValidatedEventId | None = None
    transition_turn_id: SafeTurnId
    summary_event_id: ValidatedEventId | None = None
    required_gate_event_ids: SafeEventIds = ()
    affected_work_item_ids: SafeWorkItemIds = ()
    affected_work_item_result_event_ids: SafeEventIds = ()
    reason: SafeText
    evidence_refs: SafeEventIds = ()

    @model_validator(mode="after")
    def require_transition_shape(self) -> Self:
        """Reject caller authority and dependency combinations that cannot be valid."""
        if self.transition_turn_id != self.context.turn_id:
            _reject("TRANSITION_TURN_MISMATCH")
        user_explicit = self.authority == "USER_EXPLICIT"
        requires_user = (
            self.to_status in {TicketStatus.COMPLETED, TicketStatus.CANCELLED}
            or self.from_status in {TicketStatus.COMPLETED, TicketStatus.CANCELLED}
            or (
                self.from_status is TicketStatus.IN_REVIEW
                and self.to_status is TicketStatus.IN_PROGRESS
            )
        )
        if user_explicit != requires_user:
            _reject("STATUS_AUTHORITY_SHAPE")
        if user_explicit != (self.user_decision_event_id is not None):
            _reject("STATUS_DECISION_MISMATCH")
        if user_explicit and self.user_decision_event_id not in self.context.depends_on_event_ids:
            _reject("STATUS_DECISION_DEPENDENCY_REQUIRED")
        if self.to_status is TicketStatus.IN_REVIEW:
            required = (
                self.summary_event_id,
                *self.affected_work_item_result_event_ids,
                *self.required_gate_event_ids,
            )
            if self.authority != "CODEX_RESULT" or any(item is None for item in required):
                _reject("IN_REVIEW_FACTS_REQUIRED")
            if not set(required).issubset(self.context.depends_on_event_ids):
                _reject("IN_REVIEW_DEPENDENCY_REQUIRED")
        claims = (
            self.required_gate_event_ids,
            self.affected_work_item_ids,
            self.affected_work_item_result_event_ids,
        )
        if any(len(items) != len(set(items)) for items in claims):
            _reject("DUPLICATE_REVIEW_CLAIM")
        return self


class TicketUserDecisionRequest(BoundaryModel):
    """Record one structured explicit-user decision without source text."""

    context: EventContext
    ticket_id: ValidatedTicketId
    source_turn_id: SafeTurnId
    decision: UserDecision
    decision_summary: SafeText
    content_type: SafeItem
    content_length: int = Field(ge=0, le=1_048_576)
    content_digest: ValidatedPayloadDigest


class TicketTurnSummaryRequest(BoundaryModel):
    """Record the allowlisted result summary for one turn."""

    context: EventContext
    ticket_id: ValidatedTicketId
    request_feedback_summary: SafeText
    outcome: SafeText
    change_surface: SafeItems
    verification: Annotated[tuple[VerificationPayload, ...], Field(max_length=32)]
    blockers: SafeItems
    user_decisions: SafeItems
    next_step: SafeText
    affected_work_item_ids: SafeWorkItemIds
    proposed_status: TicketStatus


class GitGateReportRequest(BoundaryModel):
    """Record read-only Git gate evidence."""

    context: EventContext
    ticket_id: ValidatedTicketId
    declared_requirement: GitRequirement
    resolved_requirement: GitRequirement
    authority_source: SafeItem
    authority_ceiling: GitRequirement
    policy_snapshot_id: SafeItem
    result: GitGateStatus
    repo_key: SafeItem
    branch: SafeItem
    head_before: GitRevision | None = None
    head_after: GitRevision | None = None
    commit_sha: GitRevision | None = None
    push_state: SafeItem
    changed_paths: SafeItems
    reason: SafeText | None = None

    @model_validator(mode="after")
    def require_matching_repository(self) -> Self:
        """Reject a gate claim for a different repository identity."""
        if self.context.repo_key != self.repo_key:
            _reject("GIT_REPOSITORY_MISMATCH")
        return self


class WikiUpdateRecordRequest(BoundaryModel):
    """Record read-only Wiki verification evidence."""

    context: EventContext
    ticket_id: ValidatedTicketId
    declared_requirement: WikiRequirement
    resolved_requirement: WikiRequirement
    result: WikiGateStatus
    wiki_root_kind: Literal["CENTRAL", "PROJECT_LOCAL"]
    policy_snapshot_id: SafeItem
    relative_paths: tuple[PurePosixPath, ...]
    section_markers: SafeItems
    sha256_before: HashMap
    sha256_after: HashMap
    required_fields_present: bool
    strict_utf8_ok: bool
    reason: SafeText | None = None

    @model_validator(mode="after")
    def require_safe_wiki_paths(self) -> Self:
        """Require traversal-free relative paths with matching digest maps."""
        paths = tuple(str(path) for path in self.relative_paths)
        if any(
            path.is_absolute() or ".." in path.parts or "\\" in raw
            for path, raw in zip(self.relative_paths, paths, strict=True)
        ):
            _reject("WIKI_PATH_INVALID")
        if set(paths) != set(self.sha256_before) or set(paths) != set(self.sha256_after):
            _reject("WIKI_DIGEST_SET_MISMATCH")
        return self


@dataclass(frozen=True, slots=True)
class SchemaContractError(ValueError):
    """Stable input-contract rejection that retains no submitted value."""

    code: str

    @override
    def __str__(self) -> str:
        return self.code


def _reject(code: str) -> Never:
    raise SchemaContractError(code)


type McpRequest = (
    TicketPreflightRequest
    | TaskUpsertRequest
    | TicketStatusUpdateRequest
    | TicketUserDecisionRequest
    | TicketTurnSummaryRequest
    | GitGateReportRequest
    | WikiUpdateRecordRequest
)
