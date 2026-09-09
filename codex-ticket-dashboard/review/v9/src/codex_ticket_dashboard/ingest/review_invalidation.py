"""IN_REVIEW dependency reconstruction and invalidation decisions."""

import sqlite3
from typing import Final, assert_never

from pydantic import TypeAdapter, ValidationError

from codex_ticket_dashboard.domain.events import ActorType, EventType
from codex_ticket_dashboard.domain.identifiers import EventId, WorkItemId
from codex_ticket_dashboard.domain.status import StatusAuthority, TicketStatus, WorkItemStatus
from codex_ticket_dashboard.domain.turns import is_connected_source_turn
from codex_ticket_dashboard.ingest.authority_models import (
    AuthorityApproved,
    AuthorityRejected,
    AuthorityResult,
    AuthoritySeam,
    InvalidateReview,
    NoReviewEffect,
    ReviewAdmissionRequest,
    ReviewEffect,
    ReviewEffectRequest,
    ReviewRetryReady,
)
from codex_ticket_dashboard.ingest.decisions import (
    consume_user_decision,
    consume_work_item_decision,
)
from codex_ticket_dashboard.ingest.payload_models import (
    GitGatePayload,
    ReviewSignalPayload,
    TurnSummaryPayload,
    WikiGatePayload,
    WorkItemPayload,
)

type EventFactRow = tuple[str, str | None, str, str, str | None, int]
_EVENT_FACTS: Final[TypeAdapter[list[EventFactRow]]] = TypeAdapter(list[EventFactRow])
_EVENT_FACT: Final[TypeAdapter[EventFactRow | None]] = TypeAdapter(EventFactRow | None)
_ID_ROWS: Final[TypeAdapter[list[tuple[str]]]] = TypeAdapter(list[tuple[str]])
_STATUS_ROW: Final[TypeAdapter[tuple[str] | None]] = TypeAdapter(tuple[str] | None)
_REVIEW_ROW: Final[TypeAdapter[tuple[str, int] | None]] = TypeAdapter(tuple[str, int] | None)
_GATE_ROWS: Final[TypeAdapter[list[tuple[str | None, str, str]]]] = TypeAdapter(
    list[tuple[str | None, str, str]]
)


def authority_seam() -> AuthoritySeam:
    """Provide the complete fail-closed authority seam for collector injection."""
    return AuthoritySeam(
        consume_user_decision,
        validate_in_review_admission,
        evaluate_review_effect,
        is_connected_source_turn,
        consume_work_item_decision,
    )


def validate_in_review_admission(
    connection: sqlite3.Connection,
    request: ReviewAdmissionRequest,
) -> AuthorityResult:
    """Reconstruct and exactly compare all current review requirements."""
    event = request.event
    payload = request.payload
    if (
        event.ticket_id is None
        or event.turn_id != payload.transition_turn_id
        or event.actor_type is not ActorType.CODEX
        or payload.authority is not StatusAuthority.CODEX_RESULT
        or payload.to_status is not TicketStatus.IN_REVIEW
    ):
        return AuthorityRejected("STATUS_AUTHORITY_REJECTED")
    active = frozenset(
        WorkItemId(row[0])
        for row in _ID_ROWS.validate_python(
            connection.execute(
                """SELECT id FROM work_items WHERE ticket_id=?
                AND status NOT IN ('CANCELLED','SUPERSEDED')""",
                (event.ticket_id,),
            ).fetchall()
        )
    )
    claimed = payload.affected_work_item_ids
    if len(claimed) != len(set(claimed)) or frozenset(claimed) != active:
        return AuthorityRejected("AFFECTED_WORK_ITEM_SET_MISMATCH")
    result_events = _result_events(connection, request)
    summary_event = _summary_event(connection, request)
    gate_events = _gate_events(connection, event.ticket_id)
    ticket_event = _ticket_creation_event(connection, event.ticket_id)
    retry_event = _retry_ready_event(connection, request)
    expected_results = frozenset(result_events.values())
    expected_dependencies = frozenset(
        (
            *expected_results,
            *gate_events,
            *(() if summary_event is None else (summary_event,)),
            *(() if ticket_event is None else (ticket_event,)),
            *(() if retry_event is None else (retry_event,)),
        )
    )
    exact = (
        set(result_events) == active
        and (payload.from_status is not TicketStatus.BLOCKED or retry_event is not None)
        and summary_event == payload.summary_event_id
        and expected_results == frozenset(payload.affected_work_item_result_event_ids)
        and gate_events == frozenset(payload.required_gate_event_ids)
        and expected_dependencies == frozenset(event.depends_on_event_ids)
        and len(event.depends_on_event_ids) == len(set(event.depends_on_event_ids))
    )
    return AuthorityApproved() if exact else AuthorityRejected("STATUS_DEPENDENCY_MISMATCH")


def evaluate_review_effect(
    connection: sqlite3.Connection,
    request: ReviewEffectRequest,
) -> ReviewEffect:
    """Return a derived effect without directly restoring ticket review state."""
    ticket_id = request.event.ticket_id
    if ticket_id is None:
        return NoReviewEffect()
    row = _STATUS_ROW.validate_python(
        connection.execute("SELECT status FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    )
    if row is None:
        return NoReviewEffect()
    status = TicketStatus(row[0])
    if status is TicketStatus.IN_REVIEW and _invalidates(request):
        return InvalidateReview(request.event.event_id)
    if status is TicketStatus.BLOCKED and _resolves(request):
        return ReviewRetryReady(request.event.event_id)
    return NoReviewEffect()


def _result_events(
    connection: sqlite3.Connection,
    request: ReviewAdmissionRequest,
) -> dict[WorkItemId, EventId]:
    rows = _EVENT_FACTS.validate_python(
        connection.execute(
            """SELECT event_id,work_item_id,payload_json,event_type,turn_id,ingest_seq
            FROM ticket_events WHERE ticket_id=? AND session_id=? AND turn_id=?
            AND event_type IN ('WORK_ITEM_CREATED','WORK_ITEM_UPDATED') AND ingest_seq<?
            ORDER BY ingest_seq DESC""",
            (
                request.event.ticket_id,
                request.event.session_id,
                request.payload.transition_turn_id,
                request.ingest_seq,
            ),
        ).fetchall()
    )
    results: dict[WorkItemId, EventId] = {}
    for event_id, work_item_id, payload_json, _event_type, _turn_id, _seq in rows:
        if work_item_id is None:
            continue
        try:
            payload = WorkItemPayload.model_validate_json(payload_json)
        except ValidationError:
            continue
        item_id = WorkItemId(work_item_id)
        if payload.status is WorkItemStatus.RESULT_REPORTED and item_id not in results:
            results[item_id] = EventId(event_id)
    return results


def _summary_event(
    connection: sqlite3.Connection,
    request: ReviewAdmissionRequest,
) -> EventId | None:
    summary_id = request.payload.summary_event_id
    if summary_id is None:
        return None
    row = _EVENT_FACT.validate_python(
        connection.execute(
            """SELECT event_id,work_item_id,payload_json,event_type,turn_id,ingest_seq
            FROM ticket_events WHERE event_id=? AND ticket_id=? AND session_id=?""",
            (summary_id, request.event.ticket_id, request.event.session_id),
        ).fetchone()
    )
    if row is None or row[3] != EventType.TURN_SUMMARIZED.value:
        return None
    try:
        summary = TurnSummaryPayload.model_validate_json(row[2])
    except ValidationError:
        return None
    return (
        EventId(row[0])
        if row[4] == request.payload.transition_turn_id
        and frozenset(summary.affected_work_item_ids)
        == frozenset(request.payload.affected_work_item_ids)
        else None
    )


def _gate_events(connection: sqlite3.Connection, ticket_id: str) -> frozenset[EventId]:
    rows = _GATE_ROWS.validate_python(
        connection.execute(
            "SELECT evidence_ref,status,requirement FROM compliance_gates WHERE ticket_id=?",
            (ticket_id,),
        ).fetchall()
    )
    allowed = {"SATISFIED", "STATUS-ONLY", "N/A"}
    return frozenset(
        EventId(reference)
        for reference, status, requirement in rows
        if reference is not None
        and status in allowed
        and requirement in {"REQUIRED", "NOT_APPLICABLE"}
    )


def _ticket_creation_event(connection: sqlite3.Connection, ticket_id: str) -> EventId | None:
    row = _STATUS_ROW.validate_python(
        connection.execute(
            """SELECT event_id FROM ticket_events WHERE ticket_id=?
            AND event_type='TICKET_CREATED' ORDER BY ingest_seq LIMIT 1""",
            (ticket_id,),
        ).fetchone()
    )
    return None if row is None else EventId(row[0])


def _retry_ready_event(
    connection: sqlite3.Connection, request: ReviewAdmissionRequest
) -> EventId | None:
    if request.payload.from_status is not TicketStatus.BLOCKED:
        return None
    row = _REVIEW_ROW.validate_python(
        connection.execute(
            """SELECT ready.event_id,ready.ingest_seq FROM ticket_events AS ready
            WHERE ready.ticket_id=? AND ready.event_type='REVIEW_RETRY_READY'
            AND ready.ingest_seq<? AND ready.ingest_seq>(SELECT COALESCE(MAX(ingest_seq),0)
            FROM ticket_events WHERE ticket_id=?
            AND event_type='REVIEW_REQUIREMENTS_INVALIDATED')
            ORDER BY ready.ingest_seq DESC LIMIT 1""",
            (request.event.ticket_id, request.ingest_seq, request.event.ticket_id),
        ).fetchone()
    )
    return None if row is None else EventId(row[0])


def _invalidates(request: ReviewEffectRequest) -> bool:
    payload = request.payload
    match payload:
        case ReviewSignalPayload(reason_code=reason):
            return (
                request.event.actor_type is ActorType.SYSTEM
                and payload.authority is StatusAuthority.SYSTEM_DERIVED
                and reason in {"POLICY_DRIFT", "SUMMARY_INCOMPLETE", "COMPLIANCE_INCOMPLETE"}
            )
        case GitGatePayload() | WikiGatePayload():
            return payload.result.value not in {"SATISFIED", "STATUS-ONLY", "N/A"}
        case TurnSummaryPayload():
            return False
        case unreachable:
            assert_never(unreachable)


def _resolves(request: ReviewEffectRequest) -> bool:
    payload = request.payload
    match payload:
        case ReviewSignalPayload(reason_code="PROJECT_POLICY_RESOLVED"):
            return (
                request.event.actor_type is ActorType.SYSTEM
                and payload.authority is StatusAuthority.SYSTEM_DERIVED
            )
        case GitGatePayload() | WikiGatePayload():
            return payload.result.value in {"SATISFIED", "STATUS-ONLY", "N/A"}
        case TurnSummaryPayload():
            return True
        case ReviewSignalPayload():
            return False
        case unreachable:
            assert_never(unreachable)
