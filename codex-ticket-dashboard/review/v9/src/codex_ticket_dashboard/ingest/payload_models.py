"""Privacy-bounded payload models shared by parser and authority projection."""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from codex_ticket_dashboard.compliance.git_gate import GitGateStatus
from codex_ticket_dashboard.compliance.policy_resolver import GitRequirement, WikiRequirement
from codex_ticket_dashboard.compliance.wiki_gate import WikiGateStatus
from codex_ticket_dashboard.domain import identifiers
from codex_ticket_dashboard.domain.events import (
    ValidatedEventId,
    ValidatedPayloadDigest,
    ValidatedWorkItemId,
)
from codex_ticket_dashboard.domain.status import (
    StatusAuthority,
    TicketStatus,
    UserDecision,
    WorkItemStatus,
)
from codex_ticket_dashboard.lifecycle.contracts import LifecyclePayload
from codex_ticket_dashboard.storage.models import RecordType

SafeText = Annotated[str, Field(min_length=1, max_length=2_000)]
SafeItem = Annotated[str, Field(min_length=1, max_length=512)]
SafeItems = Annotated[tuple[SafeItem, ...], Field(max_length=32)]
SafeTurnId = Annotated[identifiers.TurnId, Field(min_length=1, max_length=512)]
SafeEventIds = Annotated[tuple[ValidatedEventId, ...], Field(max_length=64)]
SafeWorkItemIds = Annotated[tuple[ValidatedWorkItemId, ...], Field(max_length=64)]
SafeMap = Annotated[dict[str, SafeItem], Field(max_length=32)]


class PayloadModel(BaseModel):
    """Reject unknown payload fields before durable persistence."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", hide_input_in_errors=True
    )
    authority: StatusAuthority


class ProjectPayload(PayloadModel):
    """Registry-derived project fields."""

    label: SafeItem
    logical_root_key: SafeItem
    repo_key: SafeItem
    identity_source_hash: SafeItem


class TicketPayload(PayloadModel):
    """Complete bounded ticket preflight and creation fields."""

    title: SafeItem
    record_type: RecordType
    status: TicketStatus
    needs_triage: bool
    summary: SafeText
    next_step: SafeText
    disposition: Literal["NEW_TICKET", "LINK_EXISTING", "DISCUSSION_LOG"]
    classification: Literal["TASK", "DISCUSSION", "UNCLASSIFIED"]
    goal: SafeText
    non_goals: SafeItems
    acceptance_criteria: SafeItems
    declared_git_requirement: GitRequirement
    declared_wiki_requirement: WikiRequirement


class TicketPreflightPayload(PayloadModel):
    """Bounded preflight classification retained before ticket projection."""

    disposition: Literal["NEW_TICKET", "LINK_EXISTING", "DISCUSSION_LOG"]
    classification: Literal["TASK", "DISCUSSION", "UNCLASSIFIED"]
    goal: SafeText
    non_goals: SafeItems
    acceptance_criteria: SafeItems
    declared_git_requirement: GitRequirement
    declared_wiki_requirement: WikiRequirement


class TicketLinkPayload(PayloadModel):
    """Existing-ticket preflight that also links its source thread."""

    disposition: Literal["LINK_EXISTING"]
    classification: Literal["TASK", "DISCUSSION", "UNCLASSIFIED"]
    goal: SafeText
    non_goals: SafeItems
    acceptance_criteria: SafeItems
    declared_git_requirement: GitRequirement
    declared_wiki_requirement: WikiRequirement


class WorkItemPayload(PayloadModel):
    """Complete bounded task or subtask projection fields."""

    parent_work_item_id: str | None
    kind: Literal["TASK", "SUBTASK"]
    status: WorkItemStatus
    summary: SafeText
    title: SafeItem
    acceptance_criteria: SafeItems
    user_decision_event_id: ValidatedEventId | None


class UnclassifiedActivityPayload(PayloadModel):
    """Visible triage work item emitted when structured activity is missing."""

    parent_work_item_id: str | None
    kind: Literal["UNCLASSIFIED"]
    status: WorkItemStatus
    summary: SafeText
    title: SafeItem
    acceptance_criteria: SafeItems
    user_decision_event_id: None = None


class StatusPayload(PayloadModel):
    """Complete authority and dependency claim for a ticket transition."""

    from_status: TicketStatus
    to_status: TicketStatus
    user_decision_event_id: ValidatedEventId | None
    transition_turn_id: SafeTurnId
    summary_event_id: ValidatedEventId | None
    required_gate_event_ids: SafeEventIds
    affected_work_item_ids: SafeWorkItemIds
    affected_work_item_result_event_ids: SafeEventIds
    reason: SafeText
    evidence_refs: SafeEventIds


class UserDecisionPayload(PayloadModel):
    """Structure-only explicit user decision and source metadata."""

    source_turn_id: SafeTurnId
    decision: UserDecision
    decision_summary: SafeText
    content_type: SafeItem
    content_length: int = Field(ge=0, le=1_048_576)
    content_digest: ValidatedPayloadDigest


class TurnRelationPayload(PayloadModel):
    """Explicit directed relationship between two turns."""

    source_turn_id: SafeTurnId
    related_turn_id: SafeTurnId
    relation_type: Literal["USER_FOLLOWUP", "STOP_CONTINUATION", "REOPEN_FOLLOWUP"]


class VerificationPayload(BaseModel):
    """Bounded machine-consumed verification summary item."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    check: SafeItem
    result: SafeItem
    evidence_ref: SafeItem


class TurnSummaryPayload(PayloadModel):
    """Allowlisted summary without prompt, response, or transcript text."""

    request_feedback_summary: SafeText
    outcome: SafeText
    change_surface: SafeItems
    verification: Annotated[tuple[VerificationPayload, ...], Field(max_length=32)]
    blockers: SafeItems
    user_decisions: SafeItems
    next_step: SafeText
    affected_work_item_ids: SafeWorkItemIds
    proposed_status: TicketStatus
    content_type: SafeItem
    content_length: int = Field(ge=0, le=1_048_576)
    content_digest: ValidatedPayloadDigest


class GitGatePayload(PayloadModel):
    """Allowlisted Git observation claim."""

    declared_requirement: GitRequirement
    resolved_requirement: GitRequirement
    authority_source: SafeItem
    authority_ceiling: GitRequirement
    policy_snapshot_id: SafeItem
    result: GitGateStatus
    repo_key: SafeItem
    branch: SafeItem
    head_before: SafeItem | None
    head_after: SafeItem | None
    commit_sha: SafeItem | None
    push_state: SafeItem
    changed_paths: SafeItems
    reason: SafeText | None


class WikiGatePayload(PayloadModel):
    """Allowlisted Wiki observation claim."""

    declared_requirement: WikiRequirement
    resolved_requirement: WikiRequirement
    result: WikiGateStatus
    wiki_root_kind: Literal["CENTRAL", "PROJECT_LOCAL"]
    policy_snapshot_id: SafeItem
    relative_paths: SafeItems
    section_markers: SafeItems
    sha256_before: SafeMap
    sha256_after: SafeMap
    required_fields_present: bool
    strict_utf8_ok: bool
    reason: SafeText | None


class ReviewSignalPayload(PayloadModel):
    """Structured review invalidation or resolution signal."""

    reason_code: Literal[
        "POLICY_MISMATCH",
        "POLICY_DRIFT",
        "SUMMARY_INCOMPLETE",
        "COMPLIANCE_INCOMPLETE",
        "PROJECT_POLICY_RESOLVED",
        "REVIEW_REQUIREMENTS_INVALIDATED",
        "REVIEW_RETRY_READY",
    ]
    evidence_refs: SafeEventIds


class AuthorityOnlyPayload(PayloadModel):
    """Payload for an explicitly non-projecting event marker."""


type ParsedPayload = (
    LifecyclePayload
    | ProjectPayload
    | TicketPayload
    | TicketPreflightPayload
    | TicketLinkPayload
    | WorkItemPayload
    | UnclassifiedActivityPayload
    | StatusPayload
    | UserDecisionPayload
    | TurnRelationPayload
    | TurnSummaryPayload
    | GitGatePayload
    | WikiGatePayload
    | ReviewSignalPayload
    | AuthorityOnlyPayload
)


@dataclass(frozen=True, slots=True)
class GateProjectionContext:
    """Trusted envelope fields needed to validate and project one gate."""

    project_id: identifiers.ProjectId
    ticket_id: identifiers.TicketId
    work_item_id: identifiers.WorkItemId | None
    repo_key: identifiers.RepoKey | None
    event_id: identifiers.EventId
    payload_digest: identifiers.PayloadDigest
    ingest_seq: int


_THREAD_ROW: TypeAdapter[tuple[str | None] | None] = TypeAdapter(tuple[str | None] | None)


def project_ticket_link(
    connection: sqlite3.Connection,
    session_id: identifiers.SessionId,
    project_id: identifiers.ProjectId,
    ticket_id: identifiers.TicketId,
    observed_at: datetime,
) -> bool:
    """Link a ticket without replacing an existing thread observation."""
    _ = connection.execute(
        """INSERT INTO threads VALUES (?,?,'unknown',?)
        ON CONFLICT(session_id) DO NOTHING""",
        (session_id, project_id, observed_at.isoformat()),
    )
    row = _THREAD_ROW.validate_python(
        connection.execute(
            "SELECT project_id FROM threads WHERE session_id=?", (session_id,)
        ).fetchone()
    )
    if row != (project_id,):
        return False
    _ = connection.execute(
        "INSERT OR IGNORE INTO ticket_threads VALUES (?,?)", (ticket_id, session_id)
    )
    return True


def project_work_item(
    connection: sqlite3.Connection,
    ticket_id: identifiers.TicketId,
    work_item_id: identifiers.WorkItemId,
    payload: WorkItemPayload | UnclassifiedActivityPayload,
    ingest_seq: int,
) -> None:
    """Upsert one typed work item without dropping its canonical ledger payload."""
    _ = connection.execute(
        """INSERT INTO work_items VALUES (?,?,?,?,?,?,?,1)
        ON CONFLICT(id) DO UPDATE SET parent_work_item_id=excluded.parent_work_item_id,
        status=excluded.status,summary=excluded.summary,version=work_items.version+1""",
        (
            work_item_id, ticket_id, payload.parent_work_item_id, payload.kind,
            payload.status.value, payload.summary, ingest_seq,
        ),
    )
