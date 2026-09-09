"""Typed requests, results, and protocols for Todo 7 authority functions."""

import json
import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from typing import Final, Literal, Protocol, assert_never, override

from pydantic import TypeAdapter

from codex_ticket_dashboard.domain.events import ActorType, EventOrigin, EventType
from codex_ticket_dashboard.domain.identifiers import (
    EventId,
    ProjectId,
    SessionId,
    TicketId,
    TurnId,
    new_event_id,
)
from codex_ticket_dashboard.domain.status import StatusAuthority
from codex_ticket_dashboard.ingest.dead_letter import CollectedEvent
from codex_ticket_dashboard.ingest.payload_models import (
    AuthorityOnlyPayload,
    GitGatePayload,
    ReviewSignalPayload,
    StatusPayload,
    TurnSummaryPayload,
    WikiGatePayload,
    WorkItemPayload,
)
from codex_ticket_dashboard.ingest.recovery import IdentityLink


@dataclass(frozen=True, slots=True)
class DecisionConsumptionRequest:
    """Validated ticket status event requesting a user decision consumption."""

    event: CollectedEvent
    payload: StatusPayload
    ingest_seq: int


@dataclass(frozen=True, slots=True)
class WorkItemDecisionConsumptionRequest:
    """Validated work-item removal requesting a user decision consumption."""

    event: CollectedEvent
    payload: WorkItemPayload
    ingest_seq: int


@dataclass(frozen=True, slots=True)
class ReviewAdmissionRequest:
    """Validated IN_REVIEW claim evaluated against transaction-as-of state."""

    event: CollectedEvent
    payload: StatusPayload
    ingest_seq: int


type ReviewFactPayload = (
    TurnSummaryPayload | GitGatePayload | WikiGatePayload | ReviewSignalPayload
)


@dataclass(frozen=True, slots=True)
class ReviewEffectRequest:
    """Applied fact that may invalidate or unblock review readiness."""

    event: CollectedEvent
    payload: ReviewFactPayload
    ingest_seq: int


@dataclass(frozen=True, slots=True)
class ConnectedTurnRequest:
    """Exact ticket/session pair and directed source-turn relationship."""

    ticket_id: TicketId
    session_id: SessionId
    source_turn_id: TurnId
    related_turn_id: TurnId


@dataclass(frozen=True, slots=True)
class AuthorityApproved:
    """Ticket authority validation succeeded."""

    code: Literal["ALLOWED"] = "ALLOWED"


type AuthorityFailureCode = Literal[
    "STATUS_AUTHORITY_REJECTED",
    "USER_DECISION_REJECTED",
    "AFFECTED_WORK_ITEM_SET_MISMATCH",
    "STATUS_DEPENDENCY_MISMATCH",
    "COMPLIANCE_CLAIM_REJECTED",
]


@dataclass(frozen=True, slots=True)
class AuthorityRejected:
    """Ticket authority validation failed with a stable code."""

    code: AuthorityFailureCode


type AuthorityResult = AuthorityApproved | AuthorityRejected


@dataclass(frozen=True, slots=True)
class WorkItemDecisionApproved:
    """Work-item removal decision validation succeeded."""

    code: Literal["ALLOWED"] = "ALLOWED"


@dataclass(frozen=True, slots=True)
class WorkItemDecisionRejected:
    """Work-item removal decision validation failed."""

    code: Literal["USER_DECISION_REJECTED"] = "USER_DECISION_REJECTED"


type WorkItemDecisionResult = WorkItemDecisionApproved | WorkItemDecisionRejected


@dataclass(frozen=True, slots=True)
class NoReviewEffect:
    """Applied fact leaves review state unchanged."""


@dataclass(frozen=True, slots=True)
class InvalidateReview:
    """Applied fact requires derived invalidation and BLOCKED events."""

    causation_event_id: EventId


@dataclass(frozen=True, slots=True)
class ReviewRetryReady:
    """Resolved facts require a derived retry-ready event only."""

    causation_event_id: EventId


type ReviewEffect = NoReviewEffect | InvalidateReview | ReviewRetryReady


class ConsumeUserDecision(Protocol):
    """Todo 7 ticket decision-consumption signature."""

    def __call__(self, connection: sqlite3.Connection, request: DecisionConsumptionRequest, /) -> AuthorityResult: ...  # noqa: D102, E501


class ConsumeWorkItemDecision(Protocol):
    """Todo 7 work-item decision-consumption signature."""

    def __call__(self, connection: sqlite3.Connection, request: WorkItemDecisionConsumptionRequest, /) -> WorkItemDecisionResult: ...  # noqa: D102, E501


class ValidateInReviewAdmission(Protocol):
    """Todo 7 review-dependency validation signature."""

    def __call__(self, connection: sqlite3.Connection, request: ReviewAdmissionRequest, /) -> AuthorityResult: ...  # noqa: D102, E501


class EvaluateReviewEffect(Protocol):
    """Todo 7 review-invalidation signature."""

    def __call__(self, connection: sqlite3.Connection, request: ReviewEffectRequest, /) -> ReviewEffect: ...  # noqa: D102, E501


class IsConnectedSourceTurn(Protocol):
    """Todo 7 connected-turn signature."""

    def __call__(self, connection: sqlite3.Connection, request: ConnectedTurnRequest, /) -> bool: ...  # noqa: D102, E501


@dataclass(frozen=True, slots=True)
class AuthoritySeam:
    """Injected Todo 7 pure functions used by the collector transaction."""

    consume_user_decision: ConsumeUserDecision
    validate_in_review_admission: ValidateInReviewAdmission
    evaluate_review_effect: EvaluateReviewEffect
    is_connected_source_turn: IsConnectedSourceTurn
    consume_work_item_decision: ConsumeWorkItemDecision


def _reject_decision(_connection: sqlite3.Connection, _request: DecisionConsumptionRequest) -> AuthorityResult:  # noqa: E501
    return AuthorityRejected("STATUS_AUTHORITY_REJECTED")


def _reject_review(_connection: sqlite3.Connection, _request: ReviewAdmissionRequest) -> AuthorityResult:  # noqa: E501
    return AuthorityRejected("STATUS_AUTHORITY_REJECTED")


def _no_review_effect(_connection: sqlite3.Connection, _request: ReviewEffectRequest) -> ReviewEffect:  # noqa: E501
    return NoReviewEffect()


def _not_connected(_connection: sqlite3.Connection, _request: ConnectedTurnRequest) -> bool:
    return False


def _reject_work_item(_connection: sqlite3.Connection, _request: WorkItemDecisionConsumptionRequest) -> WorkItemDecisionResult:  # noqa: E501
    return WorkItemDecisionRejected()


DEFAULT_AUTHORITY_SEAM: Final = AuthoritySeam(
    _reject_decision, _reject_review, _no_review_effect, _not_connected, _reject_work_item
)


@dataclass(frozen=True, slots=True)
class ApplyCommand:
    """Complete context for one event and projection transaction."""

    event: CollectedEvent
    effective_project_id: ProjectId | None
    archive_payload_sha256: str
    identity_link: IdentityLink | None
    authority_seam: AuthoritySeam


@dataclass(frozen=True, slots=True)
class ProjectionSchemaError(ValueError):
    """Redacted event-specific payload validation failure."""

    code: Literal["EVENT_PAYLOAD_SCHEMA_INVALID"] | AuthorityFailureCode = (
        "EVENT_PAYLOAD_SCHEMA_INVALID"
    )
    field_path: Literal[
        "payload", "payload.authority", "payload.user_decision_event_id"
    ] = "payload"

    @override
    def __str__(self) -> str:
        return f"{self.code}: field={self.field_path}"


@dataclass(frozen=True, slots=True)
class IdempotencyCollisionError(RuntimeError):
    """Different payload digest reused an existing idempotency key."""

    event_id: EventId
    code: Literal["IDEMPOTENCY_PAYLOAD_COLLISION"] = "IDEMPOTENCY_PAYLOAD_COLLISION"

    @override
    def __str__(self) -> str:
        return self.code


class DerivedEventFactory(Protocol):
    """Create one UUIDv4 event identifier inside the source transaction."""

    def __call__(self) -> EventId: ...  # noqa: D102


type DerivedPayload = AuthorityOnlyPayload | ReviewSignalPayload | StatusPayload


@dataclass(frozen=True, slots=True)
class DerivedEventWrite:
    """Complete safe event data for an in-transaction collector append."""

    source: CollectedEvent
    project_id: ProjectId
    event_type: EventType
    causation_event_id: EventId
    depends_on_event_ids: tuple[EventId, ...]
    payload: DerivedPayload


_SEQUENCE_ROW: TypeAdapter[tuple[int] | None] = TypeAdapter(tuple[int] | None)
_EVENT_ROW: TypeAdapter[tuple[str] | None] = TypeAdapter(tuple[str] | None)


def next_ingest_sequence(connection: sqlite3.Connection) -> int:
    """Reserve the next append-only collector sequence in this transaction."""
    row = _SEQUENCE_ROW.validate_python(
        connection.execute(
            """UPDATE ingest_sequences SET last_seq=last_seq+1 WHERE singleton=1
            RETURNING last_seq"""
        ).fetchone()
    )
    if row is None:
        message = "INGEST_SEQUENCE_UNAVAILABLE"
        raise sqlite3.DatabaseError(message)
    return int(row[0])


def require_authority(result: AuthorityResult) -> None:
    """Raise a redacted projection error for one rejected authority result."""
    match result:
        case AuthorityApproved():
            return
        case AuthorityRejected():
            raise ProjectionSchemaError(result.code, "payload.authority")
        case unreachable:
            assert_never(unreachable)


def append_derived_event(
    connection: sqlite3.Connection,
    write: DerivedEventWrite,
    factory: DerivedEventFactory = new_event_id,
) -> EventId:
    """Append a safe derived event and APPLIED no-spool receipt atomically."""
    payload_json = json.dumps(
        write.payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    payload_digest = "sha256:" + sha256(payload_json.encode()).hexdigest()
    key = f"{write.source.event_id}:{write.event_type.value}".encode()
    idempotency_key = "sha256:" + sha256(key).hexdigest()
    event_id = factory()
    ingest_seq = next_ingest_sequence(connection)
    source = write.source
    dependencies = write.depends_on_event_ids
    if write.event_type is EventType.STATUS_CHANGED:
        previous = _EVENT_ROW.validate_python(
            connection.execute(
                """SELECT event_id FROM ticket_events WHERE ticket_id=?
                AND event_type IN ('TICKET_CREATED','STATUS_CHANGED')
                AND ingest_seq < (SELECT ingest_seq FROM ticket_events WHERE event_id=?)
                ORDER BY ingest_seq DESC LIMIT 1""",
                (source.ticket_id, source.event_id),
            ).fetchone()
        )
        if previous is not None and previous[0] not in dependencies:
            dependencies = (*dependencies, EventId(previous[0]))
    _ = connection.execute(
        """INSERT INTO ticket_events VALUES (
        ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event_id, idempotency_key, payload_digest, write.event_type.value,
            source.schema_version, source.occurred_at.isoformat(),
            source.received_at.isoformat() if source.received_at else None,
            ActorType.SYSTEM.value, EventOrigin.COLLECTOR.value,
            StatusAuthority.SYSTEM_DERIVED.value, source.project_observation_id,
            write.project_id, "RESOLVED", source.repo_key, source.session_id,
            source.turn_id, source.ticket_id, None, write.causation_event_id,
            json.dumps(list(dependencies), separators=(",", ":")),
            payload_json, ingest_seq,
        ),
    )
    _ = connection.execute(
        """INSERT INTO ingest_receipts(
        idempotency_key,event_id,payload_digest,state,ingest_seq
        ) VALUES (?,?,?,'APPLIED',?)""",
        (idempotency_key, event_id, payload_digest, ingest_seq),
    )
    return event_id
