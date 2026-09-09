import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, ClassVar, Literal, assert_never

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field

from codex_ticket_dashboard.domain import events
from codex_ticket_dashboard.domain.events import (
    ValidatedEventId,
    ValidatedPayloadDigest,
    ValidatedTicketId,
    ValidatedWorkItemId,
)
from codex_ticket_dashboard.domain.identifiers import (
    EventId,
    IdempotencyKey,
    PayloadDigest,
    TicketId,
    WorkItemId,
    new_event_id,
)
from codex_ticket_dashboard.domain.receipts import ProjectionState
from codex_ticket_dashboard.domain.source_metadata import McpContextWitness
from codex_ticket_dashboard.ingest import payload_models, payloads
from codex_ticket_dashboard.mcp import schemas
from codex_ticket_dashboard.storage import spool


class AdmissionReceiptBase(BaseModel):
    """Common fields returned only after atomic spool acceptance."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    accepted_for_ingest: Literal[True] = True
    event_id: ValidatedEventId
    idempotency_key: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    payload_digest: ValidatedPayloadDigest
    projection_state: Literal[ProjectionState.PENDING] = ProjectionState.PENDING


class TicketAdmissionReceipt(AdmissionReceiptBase):
    """Receipt for ticket-addressed tools."""

    ticket_id: ValidatedTicketId


class WorkItemAdmissionReceipt(AdmissionReceiptBase):
    """Receipt for task_upsert."""

    work_item_id: ValidatedWorkItemId


class UserDecisionAdmissionReceipt(AdmissionReceiptBase):
    """Receipt for ticket_user_decision_record."""

    user_decision_event_id: ValidatedEventId


type AdmissionReceipt = (
    TicketAdmissionReceipt | WorkItemAdmissionReceipt | UserDecisionAdmissionReceipt
)


@dataclass(frozen=True, slots=True)
class AdmissionFacts:
    """Trusted server-derived fields for one atomic MCP admission."""

    event_type: events.EventType
    actor_type: events.ActorType
    context: schemas.EventContext
    ticket_id: TicketId | None
    work_item_id: WorkItemId | None
    receipt_kind: Literal["TICKET", "WORK_ITEM", "DECISION"]


@dataclass(frozen=True, slots=True)
class ReceiptRequest:
    """Complete server-derived receipt identity."""

    kind: Literal["TICKET", "WORK_ITEM", "DECISION"]
    event_id: EventId
    ticket_id: TicketId | None
    work_item_id: WorkItemId | None
    idempotency_key: IdempotencyKey
    payload_digest: PayloadDigest


def receipt_from(request: ReceiptRequest) -> AdmissionReceipt:
    """Build the tool-specific receipt without a generic entity alias."""
    match request.kind:
        case "TICKET":
            if request.ticket_id is None:
                raise ReceiptConstructionError
            return TicketAdmissionReceipt(
                event_id=request.event_id,
                ticket_id=request.ticket_id,
                idempotency_key=request.idempotency_key,
                payload_digest=request.payload_digest,
            )
        case "WORK_ITEM":
            if request.work_item_id is None:
                raise ReceiptConstructionError
            return WorkItemAdmissionReceipt(
                event_id=request.event_id,
                work_item_id=request.work_item_id,
                idempotency_key=request.idempotency_key,
                payload_digest=request.payload_digest,
            )
        case "DECISION":
            return UserDecisionAdmissionReceipt(
                event_id=request.event_id,
                user_decision_event_id=request.event_id,
                idempotency_key=request.idempotency_key,
                payload_digest=request.payload_digest,
            )
        case unreachable:
            assert_never(unreachable)


def admit_event(
    writer: spool.SpoolWriter,
    request: schemas.McpRequest,
    payload: payload_models.ParsedPayload,
    facts: AdmissionFacts,
    *,
    witness: McpContextWitness | None = None,
) -> AdmissionReceipt:
    """Atomically admit one validated event and return only a pending receipt."""
    event_id = new_event_id()
    payload_json = payloads.canonical_payload_json(payload)
    payload_digest = PayloadDigest("sha256:" + sha256(payload_json.encode()).hexdigest())
    context = facts.context
    request_json = json.dumps(
        request.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    if witness is not None:
        request_json += witness.model_dump_json()
    request_hash = sha256(request_json.encode()).hexdigest()
    key_material = (
        f"1:{context.session_id}:{context.turn_id}:{facts.event_type.value}:"
        f"{type(request).__name__}:{request_hash}"
    ).encode()
    idempotency_key = IdempotencyKey("sha256:" + sha256(key_material).hexdigest())
    envelope = events.EventEnvelope[payload_models.ParsedPayload](
        schema_version=1,
        event_id=event_id,
        event_type=facts.event_type,
        occurred_at=datetime.now(UTC),
        received_at=None,
        actor_type=facts.actor_type,
        origin=events.EventOrigin.MCP_TOOL,
        project_observation_id=context.project_observation_id,
        project_id=context.project_id,
        project_resolution_state=events.ProjectResolutionState.RESOLVED,
        repo_key=context.repo_key,
        session_id=context.session_id,
        turn_id=context.turn_id,
        ticket_id=facts.ticket_id,
        work_item_id=facts.work_item_id,
        causation_event_id=context.causation_event_id,
        depends_on_event_ids=context.depends_on_event_ids,
        payload=payload,
        idempotency_key=idempotency_key,
        payload_digest=payload_digest,
        mcp_context=witness,
    )
    match writer.write(envelope):
        case spool.SpoolAccepted() | spool.SpoolExisting():
            return receipt_from(
                ReceiptRequest(
                    facts.receipt_kind,
                    event_id,
                    facts.ticket_id,
                    facts.work_item_id,
                    idempotency_key,
                    payload_digest,
                )
            )
        case spool.SpoolCollision() as collision:
            raise ToolError(collision.code)
        case unreachable:
            assert_never(unreachable)


class ReceiptConstructionError(RuntimeError):
    """Signal an impossible missing server-derived entity identifier."""
