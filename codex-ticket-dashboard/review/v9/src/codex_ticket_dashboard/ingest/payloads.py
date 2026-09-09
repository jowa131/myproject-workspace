"""Closed, privacy-bounded payload variants for collector projection."""

import json
import sqlite3
from datetime import datetime
from hashlib import sha256
from pathlib import PurePosixPath
from typing import assert_never

from pydantic import JsonValue, TypeAdapter

from codex_ticket_dashboard.compliance.git_gate import GitEvidence, evaluate_git_gate
from codex_ticket_dashboard.compliance.policy_resolver import (
    GitRequirement,
    ProjectPolicy,
    WikiRequirement,
)
from codex_ticket_dashboard.compliance.wiki_gate import (
    WikiEvidence,
    WikiFileEvidence,
    evaluate_wiki_gate,
)
from codex_ticket_dashboard.domain.events import EventType
from codex_ticket_dashboard.domain.identifiers import TicketId
from codex_ticket_dashboard.domain.status import TicketStatus, UserDecision
from codex_ticket_dashboard.ingest.payload_models import (
    AuthorityOnlyPayload,
    GateProjectionContext,
    GitGatePayload,
    ParsedPayload,
    ProjectPayload,
    ReviewSignalPayload,
    StatusPayload,
    TicketLinkPayload,
    TicketPayload,
    TicketPreflightPayload,
    TurnRelationPayload,
    TurnSummaryPayload,
    UnclassifiedActivityPayload,
    UserDecisionPayload,
    VerificationPayload,
    WikiGatePayload,
    WorkItemPayload,
)
from codex_ticket_dashboard.lifecycle.contracts import LIFECYCLE_EVENT_TYPES, LifecycleRecord

__all__ = ["VerificationPayload"]


def parse_payload(  # noqa: C901, PLR0911, PLR0912
    event_type: EventType, value: JsonValue
) -> ParsedPayload:
    """Parse one event through its exact payload schema."""
    if (
        event_type.value in LIFECYCLE_EVENT_TYPES
        and isinstance(value, dict)
        and "lifecycle_version" in value
    ):
        record = LifecycleRecord.model_validate({"event_type": event_type.value, "payload": value})
        return record.payload
    match event_type:
        case EventType.PROJECT_IDENTITY_RESOLVED:
            return ProjectPayload.model_validate(value)
        case EventType.TICKET_CREATED:
            return TicketPayload.model_validate(value)
        case EventType.TICKET_PREFLIGHT_RECORDED:
            return TicketPreflightPayload.model_validate(value)
        case EventType.TICKET_LINKED_TO_THREAD:
            return TicketLinkPayload.model_validate(value)
        case EventType.WORK_ITEM_CREATED | EventType.WORK_ITEM_UPDATED:
            return WorkItemPayload.model_validate(value)
        case EventType.UNCLASSIFIED_ACTIVITY_CREATED:
            return UnclassifiedActivityPayload.model_validate(value)
        case EventType.STATUS_CHANGED:
            return StatusPayload.model_validate(value)
        case EventType.USER_DECISION_RECORDED:
            return UserDecisionPayload.model_validate(value)
        case EventType.TURN_RELATION_RECORDED:
            return TurnRelationPayload.model_validate(value)
        case EventType.TURN_SUMMARIZED:
            return TurnSummaryPayload.model_validate(value)
        case EventType.GIT_GATE_REPORTED:
            return GitGatePayload.model_validate(value)
        case EventType.WIKI_GATE_REPORTED:
            return WikiGatePayload.model_validate(value)
        case (
            EventType.POLICY_MISMATCH
            | EventType.POLICY_DRIFT
            | EventType.SUMMARY_INCOMPLETE
            | EventType.COMPLIANCE_INCOMPLETE
            | EventType.PROJECT_POLICY_RESOLVED
            | EventType.REVIEW_REQUIREMENTS_INVALIDATED
            | EventType.REVIEW_RETRY_READY
        ):
            return ReviewSignalPayload.model_validate(value)
        case (
            EventType.THREAD_OBSERVED
            | EventType.THREAD_OBSERVATION_ENDED
            | EventType.USER_FEEDBACK_OBSERVED
            | EventType.STATUS_CONFLICT
            | EventType.STATUS_AUTHORITY_REJECTED
            | EventType.USER_DECISION_REJECTED
            | EventType.HOOK_DECISION_RECORDED
            | EventType.HOOK_AGGREGATE_OUTCOME_OBSERVED
            | EventType.CONTINUATION_LIMIT_REACHED
            | EventType.IDEMPOTENCY_PAYLOAD_COLLISION
            | EventType.PROJECT_IDENTITY_CONFLICT
            | EventType.DEPENDENCY_PENDING
            | EventType.DEPENDENCY_APPLIED
            | EventType.DEPENDENCY_FAILED
            | EventType.NO_ACTIVE_WORK_ITEMS
            | EventType.TOOL_RECEIPT_MISMATCH
            | EventType.PLAN_OBSERVED
            | EventType.SUBAGENT_STARTED
            | EventType.SUBAGENT_STOPPED
            | EventType.TURN_STOPPED
            | EventType.INGEST_RECOVERED
            | EventType.INGEST_REJECTED
            | EventType.TICKET_REOPENED
            | EventType.TICKET_CLOSED
        ):
            return AuthorityOnlyPayload.model_validate(value)
        case unreachable:
            assert_never(unreachable)


def canonical_payload_json(payload: ParsedPayload) -> str:
    return json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


type PolicyRow = tuple[str, str, str, str, str, str, str]
_POLICY_ROW: TypeAdapter[PolicyRow | None] = TypeAdapter(PolicyRow | None)
_TEXT_ROW: TypeAdapter[tuple[str] | None] = TypeAdapter(tuple[str] | None)


def read_ticket_status(connection: sqlite3.Connection, ticket_id: TicketId) -> TicketStatus | None:
    """Read the exact current status inside the source transaction."""
    row = _TEXT_ROW.validate_python(
        connection.execute("SELECT status FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    )
    return None if row is None else TicketStatus(row[0])


def read_user_decision(connection: sqlite3.Connection, event_id: str | None) -> UserDecision | None:
    """Read only the typed decision enum from a canonical ledger payload."""
    if event_id is None:
        return None
    row = _TEXT_ROW.validate_python(
        connection.execute(
            "SELECT payload_json FROM ticket_events WHERE event_id=?", (event_id,)
        ).fetchone()
    )
    return None if row is None else UserDecisionPayload.model_validate_json(row[0]).decision


def project_ticket_status(
    connection: sqlite3.Connection,
    ticket_id: TicketId,
    occurred_at: datetime,
    payload: StatusPayload,
) -> bool:
    """Update state and terminal closure fields together after authority validation."""
    terminal = payload.to_status in {TicketStatus.COMPLETED, TicketStatus.CANCELLED}
    reopened = payload.to_status is TicketStatus.PLANNED
    closed_at = occurred_at.isoformat() if terminal else None
    closed_reason = payload.reason if terminal else None
    cursor = connection.execute(
        """UPDATE tickets SET status=?,updated_at=?,
        closed_at=CASE WHEN ? THEN ? WHEN ? THEN NULL ELSE closed_at END,
        closed_reason=CASE WHEN ? THEN ? WHEN ? THEN NULL ELSE closed_reason END,
        version=version+1 WHERE id=? AND status=?""",
        (
            payload.to_status.value,
            occurred_at.isoformat(),
            terminal,
            closed_at,
            reopened,
            terminal,
            closed_reason,
            reopened,
            ticket_id,
            payload.from_status.value,
        ),
    )
    return cursor.rowcount == 1


def project_turn_summary(
    connection: sqlite3.Connection,
    ticket_id: TicketId,
    occurred_at: datetime,
    payload: TurnSummaryPayload,
) -> None:
    """Project bounded summary fields without changing review state directly."""
    _ = connection.execute(
        """UPDATE tickets SET summary=?,next_step=?,updated_at=?,version=version+1
        WHERE id=?""",
        (payload.outcome, payload.next_step, occurred_at.isoformat(), ticket_id),
    )


def project_compliance_gate(  # noqa: C901, PLR0911
    connection: sqlite3.Connection,
    context: GateProjectionContext,
    payload: GitGatePayload | WikiGatePayload,
) -> bool:
    """Recompute a reported gate from current policy and bounded evidence."""
    row = _POLICY_ROW.validate_python(
        connection.execute(
            """SELECT p.repo_key,pp.wiki_authority,pp.git_authority,
            pp.authority_ceiling,pp.evidence_ref,pp.evidence_hash,pp.policy_snapshot_id
            FROM projects p JOIN project_policies pp ON pp.project_id=p.id WHERE p.id=?""",
            (context.project_id,),
        ).fetchone()
    )
    if row is None:
        return False
    repo_key, wiki_raw, git_raw, ceiling_raw, source_ref, source_hash, snapshot = row
    policy = ProjectPolicy(
        context.project_id,
        GitRequirement(git_raw),
        GitRequirement(ceiling_raw),
        WikiRequirement(wiki_raw),
        source_ref,
        source_hash,
        snapshot,
        source_hash,
    )
    if (
        payload.policy_snapshot_id != snapshot
        or payload.declared_requirement != payload.resolved_requirement
    ):
        return False
    if isinstance(payload, GitGatePayload):
        if context.repo_key != repo_key or payload.repo_key != repo_key:
            return False
        if (
            payload.resolved_requirement is not policy.git_requirement
            or payload.authority_ceiling is not policy.authority_ceiling
            or payload.authority_source != policy.source_ref
        ):
            return False
        paths = tuple(PurePosixPath(path) for path in payload.changed_paths)
        pushed = payload.commit_sha if payload.push_state == "PUSHED" else None
        evidence = GitEvidence(
            True, paths, payload.commit_sha, paths, pushed, pushed,  # noqa: FBT003
        )
        assessment = evaluate_git_gate(policy, payload.declared_requirement, evidence)
        if assessment.status != payload.result:
            return False
        gate_type = "GIT"
    else:
        if payload.resolved_requirement is not policy.wiki_requirement:
            return False
        root_kind = (
            "CENTRAL"
            if policy.wiki_requirement is WikiRequirement.CENTRAL_WIKI
            else "PROJECT_LOCAL"
        )
        if payload.wiki_root_kind != root_kind:
            return False
        paths_set = set(payload.relative_paths)
        if paths_set != set(payload.sha256_before) or paths_set != set(payload.sha256_after):
            return False
        evidence = WikiEvidence(
            files=tuple(
                WikiFileEvidence(
                    PurePosixPath(path),
                    payload.sha256_before[path],
                    payload.sha256_after[path],
                )
                for path in payload.relative_paths
            ),
            section_markers=payload.section_markers,
            required_fields_present=payload.required_fields_present,
            strict_utf8_ok=payload.strict_utf8_ok,
            generated_projection_target=False,
        )
        assessment = evaluate_wiki_gate(policy, payload.declared_requirement, evidence)
        if assessment.status != payload.result:
            return False
        gate_type = "WIKI"
    resolved = payload.resolved_requirement.value
    requirement = "NOT_APPLICABLE" if resolved == "NOT_APPLICABLE" else "REQUIRED"
    gate_id = "gate_" + sha256(f"{context.ticket_id}:{gate_type}".encode()).hexdigest()[:24]
    _ = connection.execute(
        """INSERT INTO compliance_gates VALUES (?,?,?,?,?,?,?,?,?,?,1)
        ON CONFLICT(id) DO UPDATE SET requirement=excluded.requirement,
        status=excluded.status,evidence_ref=excluded.evidence_ref,
        evidence_hash=excluded.evidence_hash,version=compliance_gates.version+1""",
        (
            gate_id,
            context.project_id,
            context.ticket_id,
            context.work_item_id,
            gate_type,
            requirement,
            payload.result.value,
            context.event_id,
            context.payload_digest,
            context.ingest_seq,
        ),
    )
    return True
