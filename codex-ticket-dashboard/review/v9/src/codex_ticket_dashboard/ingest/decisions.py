"""Atomic explicit-user decision validation and consumption."""

import sqlite3
from typing import Final

from pydantic import TypeAdapter, ValidationError

from codex_ticket_dashboard.domain.events import ActorType, EventType
from codex_ticket_dashboard.domain.identifiers import EventId
from codex_ticket_dashboard.domain.status import (
    StatusAuthority,
    TicketStatus,
    TicketTransition,
    TransitionAllowed,
    UserDecision,
    evaluate_ticket_transition,
)
from codex_ticket_dashboard.domain.turns import is_connected_source_turn
from codex_ticket_dashboard.ingest.authority_models import (
    AuthorityApproved,
    AuthorityRejected,
    AuthorityResult,
    ConnectedTurnRequest,
    DecisionConsumptionRequest,
    WorkItemDecisionApproved,
    WorkItemDecisionConsumptionRequest,
    WorkItemDecisionRejected,
    WorkItemDecisionResult,
)
from codex_ticket_dashboard.ingest.payload_models import UserDecisionPayload

type DecisionRow = tuple[str, str | None, str, str | None, str, str, str, int]
_DECISION_ROW: Final[TypeAdapter[DecisionRow | None]] = TypeAdapter(DecisionRow | None)
_SEQUENCE_ROW: Final[TypeAdapter[tuple[int] | None]] = TypeAdapter(tuple[int] | None)
_CONSUMED_ROW: Final[TypeAdapter[tuple[int] | None]] = TypeAdapter(tuple[int] | None)

_COMPATIBLE: Final = frozenset(
    {
        (TicketStatus.IN_REVIEW, TicketStatus.COMPLETED, UserDecision.ACCEPT),
        (TicketStatus.IN_PROGRESS, TicketStatus.CANCELLED, UserDecision.CANCEL),
        (TicketStatus.WAITING_USER, TicketStatus.CANCELLED, UserDecision.CANCEL),
        (TicketStatus.BLOCKED, TicketStatus.CANCELLED, UserDecision.CANCEL),
        (TicketStatus.IN_REVIEW, TicketStatus.CANCELLED, UserDecision.CANCEL),
        (TicketStatus.BACKLOG, TicketStatus.CANCELLED, UserDecision.CANCEL),
        (TicketStatus.PLANNED, TicketStatus.CANCELLED, UserDecision.CANCEL),
        (TicketStatus.IN_REVIEW, TicketStatus.IN_PROGRESS, UserDecision.REOPEN),
        (TicketStatus.IN_REVIEW, TicketStatus.IN_PROGRESS, UserDecision.SCOPE_CHANGE),
        (TicketStatus.COMPLETED, TicketStatus.PLANNED, UserDecision.REOPEN),
        (TicketStatus.COMPLETED, TicketStatus.PLANNED, UserDecision.SCOPE_CHANGE),
        (TicketStatus.CANCELLED, TicketStatus.PLANNED, UserDecision.REOPEN),
    }
)


def decision_matches_transition(
    source: TicketStatus,
    target: TicketStatus,
    decision: UserDecision,
) -> bool:
    """Return whether one explicit decision authorizes exactly one transition."""
    return (source, target, decision) in _COMPATIBLE


def consume_user_decision(
    connection: sqlite3.Connection,
    request: DecisionConsumptionRequest,
) -> AuthorityResult:
    """Validate and consume a decision inside the caller's projection transaction."""
    event = request.event
    decision_id = request.payload.user_decision_event_id
    ticket_id = event.ticket_id
    if (
        decision_id is None
        or ticket_id is None
        or event.turn_id != request.payload.transition_turn_id
    ):
        return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
    row = _DECISION_ROW.validate_python(
        connection.execute(
            """SELECT event_type,ticket_id,session_id,turn_id,actor_type,authority,
            payload_json,ingest_seq FROM ticket_events WHERE event_id=?""",
            (decision_id,),
        ).fetchone()
    )
    if row is None:
        return AuthorityRejected("USER_DECISION_REJECTED")
    try:
        decision = UserDecisionPayload.model_validate_json(row[6])
    except ValidationError:
        return AuthorityRejected("USER_DECISION_REJECTED")
    consumed = _CONSUMED_ROW.validate_python(
        connection.execute(
            "SELECT 1 FROM decision_consumptions WHERE decision_event_id=?",
            (decision_id,),
        ).fetchone()
    )
    baseline = _status_baseline(connection, ticket_id, request.ingest_seq)
    connected = is_connected_source_turn(
        connection,
        ConnectedTurnRequest(
            ticket_id,
            event.session_id,
            decision.source_turn_id,
            request.payload.transition_turn_id,
        ),
    )
    identity_matches = row[:6] == (
        EventType.USER_DECISION_RECORDED.value,
        ticket_id,
        event.session_id,
        decision.source_turn_id,
        ActorType.USER.value,
        StatusAuthority.USER_EXPLICIT.value,
    )
    dependency_matches = EventId(decision_id) in event.depends_on_event_ids
    transition = TicketTransition(
        request.payload.from_status,
        request.payload.to_status,
        request.payload.authority,
        event.actor_type,
        decision.decision,
        decision_is_fresh=row[7] > baseline,
        decision_is_consumed=consumed is not None,
        has_causation=event.causation_event_id is not None,
    )
    authority = evaluate_ticket_transition(transition)
    if not identity_matches or not connected or not dependency_matches:
        return AuthorityRejected("USER_DECISION_REJECTED")
    if not decision_matches_transition(
        request.payload.from_status,
        request.payload.to_status,
        decision.decision,
    ) or not isinstance(authority, TransitionAllowed):
        return AuthorityRejected("USER_DECISION_REJECTED")
    _ = connection.execute(
        "INSERT INTO decision_consumptions VALUES (?,?,?,?)",
        (decision_id, ticket_id, event.event_id, request.ingest_seq),
    )
    return AuthorityApproved()


def consume_work_item_decision(
    connection: sqlite3.Connection,
    request: WorkItemDecisionConsumptionRequest,
) -> WorkItemDecisionResult:
    """Consume the exact decision required to remove one active work item."""
    event = request.event
    decision_id = request.payload.user_decision_event_id
    ticket_id = event.ticket_id
    if decision_id is None or ticket_id is None or event.turn_id is None:
        return WorkItemDecisionRejected()
    row = _DECISION_ROW.validate_python(
        connection.execute(
            """SELECT event_type,ticket_id,session_id,turn_id,actor_type,authority,
            payload_json,ingest_seq FROM ticket_events WHERE event_id=?""",
            (decision_id,),
        ).fetchone()
    )
    if row is None:
        return WorkItemDecisionRejected()
    try:
        decision = UserDecisionPayload.model_validate_json(row[6])
    except ValidationError:
        return WorkItemDecisionRejected()
    consumed = _CONSUMED_ROW.validate_python(
        connection.execute(
            "SELECT 1 FROM decision_consumptions WHERE decision_event_id=?",
            (decision_id,),
        ).fetchone()
    )
    required = {
        "CANCELLED": UserDecision.CANCEL,
        "SUPERSEDED": UserDecision.SCOPE_CHANGE,
    }.get(request.payload.status.value)
    connected = is_connected_source_turn(
        connection,
        ConnectedTurnRequest(
            ticket_id,
            event.session_id,
            decision.source_turn_id,
            event.turn_id,
        ),
    )
    identity_matches = row[:6] == (
        EventType.USER_DECISION_RECORDED.value,
        ticket_id,
        event.session_id,
        decision.source_turn_id,
        ActorType.USER.value,
        StatusAuthority.USER_EXPLICIT.value,
    )
    baseline = _work_item_baseline(connection, event.work_item_id, request.ingest_seq)
    valid = (
        required is not None
        and decision.decision is required
        and row[7] > baseline
        and consumed is None
        and identity_matches
        and connected
        and EventId(decision_id) in event.depends_on_event_ids
        and request.payload.authority is StatusAuthority.USER_EXPLICIT
        and event.actor_type is ActorType.USER
    )
    if not valid:
        return WorkItemDecisionRejected()
    _ = connection.execute(
        "INSERT INTO decision_consumptions VALUES (?,?,?,?)",
        (decision_id, ticket_id, event.event_id, request.ingest_seq),
    )
    return WorkItemDecisionApproved()


def _status_baseline(
    connection: sqlite3.Connection,
    ticket_id: str,
    before_ingest_seq: int,
) -> int:
    row = _SEQUENCE_ROW.validate_python(
        connection.execute(
            """SELECT MAX(ingest_seq) FROM ticket_events
            WHERE ticket_id=? AND event_type IN ('TICKET_CREATED','STATUS_CHANGED')
            AND ingest_seq<?""",
            (ticket_id, before_ingest_seq),
        ).fetchone()
    )
    return 0 if row is None or row[0] is None else row[0]


def _work_item_baseline(
    connection: sqlite3.Connection,
    work_item_id: str | None,
    before_ingest_seq: int,
) -> int:
    if work_item_id is None:
        return before_ingest_seq
    row = _SEQUENCE_ROW.validate_python(
        connection.execute(
            """SELECT MAX(ingest_seq) FROM ticket_events
            WHERE work_item_id=? AND event_type IN ('WORK_ITEM_CREATED','WORK_ITEM_UPDATED')
            AND ingest_seq<?""",
            (work_item_id, before_ingest_seq),
        ).fetchone()
    )
    return 0 if row is None or row[0] is None else row[0]
