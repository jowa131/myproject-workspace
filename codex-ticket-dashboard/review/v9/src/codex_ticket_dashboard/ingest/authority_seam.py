"""Typed pure-function boundary for Todo 7 authority decisions."""

import sqlite3
from typing import assert_never

from codex_ticket_dashboard.domain.events import ActorType, EventOrigin, EventType
from codex_ticket_dashboard.domain.identifiers import EventId, ProjectId
from codex_ticket_dashboard.domain.status import (
    StatusAuthority,
    TicketStatus,
    TicketTransition,
    TransitionAllowed,
    TransitionRejected,
    evaluate_ticket_transition,
)
from codex_ticket_dashboard.ingest import payloads as event_payloads
from codex_ticket_dashboard.ingest.authority_models import (
    AuthorityApproved,
    AuthorityRejected,
    AuthorityResult,
    AuthoritySeam,
    DecisionConsumptionRequest,
    DerivedEventWrite,
    InvalidateReview,
    NoReviewEffect,
    ReviewAdmissionRequest,
    ReviewEffectRequest,
    ReviewFactPayload,
    ReviewRetryReady,
    append_derived_event,
)
from codex_ticket_dashboard.ingest.dead_letter import CollectedEvent
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
    WikiGatePayload,
    WorkItemPayload,
)


def project_authority_payload(  # noqa: C901, PLR0911, PLR0912, PLR0913, PLR0917
    connection: sqlite3.Connection, event: CollectedEvent, payload: ParsedPayload,
    ingest_seq: int, project_id: ProjectId | None, seam: AuthoritySeam,
) -> AuthorityResult:
    """Project one authority payload through the injected Todo 7 seam."""
    match payload:
        case StatusPayload() as status:
            if event.ticket_id is None:
                return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            current = event_payloads.read_ticket_status(connection, event.ticket_id)
            if current is None:
                return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            if current is not status.from_status:
                if project_id is None:
                    return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
                conflict = AuthorityOnlyPayload(authority=StatusAuthority.SYSTEM_DERIVED)
                _ = append_derived_event(
                    connection,
                    DerivedEventWrite(
                        event, project_id, EventType.STATUS_CONFLICT,
                        event.event_id, (event.event_id,), conflict,
                    ),
                )
                return AuthorityApproved()
            decision_value = None
            if status.authority is StatusAuthority.USER_EXPLICIT:
                decision = seam.consume_user_decision(
                    connection, DecisionConsumptionRequest(event, status, ingest_seq)
                )
                if isinstance(decision, AuthorityRejected):
                    return decision
                decision_value = event_payloads.read_user_decision(
                    connection, status.user_decision_event_id
                )
            if (
                status.authority is StatusAuthority.SYSTEM_DERIVED
                and event.origin is not EventOrigin.COLLECTOR
            ):
                return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            transition = evaluate_ticket_transition(
                TicketTransition(
                    from_status=status.from_status,
                    to_status=status.to_status,
                    authority=status.authority,
                    actor_type=event.actor_type,
                    decision=decision_value,
                    decision_is_fresh=decision_value is not None,
                    decision_is_consumed=False,
                    has_causation=event.causation_event_id is not None,
                )
            )
            match transition:
                case TransitionRejected():
                    return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
                case TransitionAllowed():
                    pass
                case unreachable:
                    assert_never(unreachable)
            if status.to_status is TicketStatus.IN_REVIEW:
                admission = seam.validate_in_review_admission(
                    connection, ReviewAdmissionRequest(event, status, ingest_seq)
                )
                if isinstance(admission, AuthorityRejected):
                    return admission
            return (
                AuthorityApproved()
                if event_payloads.project_ticket_status(
                    connection, event.ticket_id, event.occurred_at, status
                )
                else AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            )
        case TurnSummaryPayload() as summary:
            if event.ticket_id is None:
                return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            event_payloads.project_turn_summary(
                connection, event.ticket_id, event.occurred_at, summary
            )
            return _review_effect(connection, event, summary, ingest_seq, project_id, seam)
        case GitGatePayload() | WikiGatePayload() as gate:
            if event.ticket_id is None or project_id is None:
                return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            valid = event_payloads.project_compliance_gate(
                connection,
                GateProjectionContext(
                    project_id, event.ticket_id, event.work_item_id, event.repo_key,
                    event.event_id, event.payload_digest, ingest_seq,
                ),
                gate,
            )
            if not valid:
                return AuthorityRejected("COMPLIANCE_CLAIM_REJECTED")
            return _review_effect(connection, event, gate, ingest_seq, project_id, seam)
        case TurnRelationPayload() as relation:
            if event.ticket_id is None:
                return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            _ = connection.execute(
                "INSERT INTO turn_relations VALUES (?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.ticket_id,
                    event.session_id,
                    relation.source_turn_id,
                    relation.related_turn_id,
                    relation.relation_type,
                ),
            )
            return AuthorityApproved()
        case ReviewSignalPayload() as signal:
            return _review_effect(connection, event, signal, ingest_seq, project_id, seam)
        case UserDecisionPayload() | AuthorityOnlyPayload():
            return AuthorityApproved()
        case (
            ProjectPayload() | TicketPayload() | TicketPreflightPayload()
            | TicketLinkPayload() | WorkItemPayload() | UnclassifiedActivityPayload()
        ):
            return AuthorityApproved()
        case unreachable:
            assert_never(unreachable)


def _review_effect(  # noqa: PLR0913, PLR0917
    connection: sqlite3.Connection, event: CollectedEvent, payload: ReviewFactPayload,
    ingest_seq: int, project_id: ProjectId | None, seam: AuthoritySeam,
) -> AuthorityResult:
    effect = seam.evaluate_review_effect(
        connection, ReviewEffectRequest(event, payload, ingest_seq)
    )
    match effect:
        case NoReviewEffect():
            return AuthorityApproved()
        case ReviewRetryReady(causation_event_id=causation):
            if event.ticket_id is None or project_id is None:
                return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
            signal = ReviewSignalPayload(
                authority=StatusAuthority.SYSTEM_DERIVED,
                reason_code="REVIEW_RETRY_READY",
                evidence_refs=(causation,),
            )
            _ = append_derived_event(
                connection,
                DerivedEventWrite(
                    event, project_id, EventType.REVIEW_RETRY_READY,
                    causation, (causation,), signal,
                ),
            )
            return AuthorityApproved()
        case InvalidateReview(causation_event_id=causation):
            return _append_invalidation(connection, event, project_id, causation)
        case unreachable:
            assert_never(unreachable)


def _append_invalidation(
    connection: sqlite3.Connection, event: CollectedEvent,
    project_id: ProjectId | None, causation: EventId,
) -> AuthorityResult:
    if event.ticket_id is None or event.turn_id is None or project_id is None:
        return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
    signal = ReviewSignalPayload(
        authority=StatusAuthority.SYSTEM_DERIVED,
        reason_code="REVIEW_REQUIREMENTS_INVALIDATED",
        evidence_refs=(causation,),
    )
    invalidation_id = append_derived_event(
        connection,
        DerivedEventWrite(
            event, project_id, EventType.REVIEW_REQUIREMENTS_INVALIDATED,
            causation, (causation,), signal,
        ),
    )
    status = StatusPayload(
        authority=StatusAuthority.SYSTEM_DERIVED,
        from_status=TicketStatus.IN_REVIEW,
        to_status=TicketStatus.BLOCKED,
        user_decision_event_id=None,
        transition_turn_id=event.turn_id,
        summary_event_id=None,
        required_gate_event_ids=(),
        affected_work_item_ids=(),
        affected_work_item_result_event_ids=(),
        reason="Review requirements invalidated",
        evidence_refs=(causation, invalidation_id),
    )
    transition = evaluate_ticket_transition(
        TicketTransition(
            TicketStatus.IN_REVIEW, TicketStatus.BLOCKED,
            StatusAuthority.SYSTEM_DERIVED, ActorType.SYSTEM,
            has_causation=True,
        )
    )
    if isinstance(transition, TransitionRejected):
        return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
    _ = append_derived_event(
        connection,
        DerivedEventWrite(
            event, project_id, EventType.STATUS_CHANGED,
            causation, (causation, invalidation_id), status,
        ),
    )
    return (
        AuthorityApproved()
        if event_payloads.project_ticket_status(
            connection, event.ticket_id, event.occurred_at, status
        )
        else AuthorityRejected("STATUS_AUTHORITY_REJECTED")
    )
