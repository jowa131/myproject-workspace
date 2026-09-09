"""Typed event parsing and atomic SQLite projection."""

import json
import sqlite3
from typing import Final, assert_never

from pydantic import TypeAdapter, ValidationError

from codex_ticket_dashboard.domain.events import EventType
from codex_ticket_dashboard.domain.status import WorkItemStatus
from codex_ticket_dashboard.ingest import authority_seam as authority
from codex_ticket_dashboard.ingest.authority_models import (
    ApplyCommand,
    IdempotencyCollisionError,
    ProjectionSchemaError,
    WorkItemDecisionApproved,
    WorkItemDecisionConsumptionRequest,
    WorkItemDecisionRejected,
    next_ingest_sequence,
    require_authority,
)
from codex_ticket_dashboard.ingest.continuation_projection import project_continuation
from codex_ticket_dashboard.ingest.dead_letter import parse_event_payload
from codex_ticket_dashboard.ingest.lifecycle_projection import (
    apply_lifecycle,
    persist_mcp_witness,
    refresh_activity_links,
)
from codex_ticket_dashboard.ingest.payload_models import (
    ParsedPayload,
    PayloadModel,
    ProjectPayload,
    TicketLinkPayload,
    TicketPayload,
    UnclassifiedActivityPayload,
    WorkItemPayload,
    project_ticket_link,
    project_work_item,
)
from codex_ticket_dashboard.ingest.payloads import canonical_payload_json
from codex_ticket_dashboard.ingest.recovery import (
    IdentityLinkWrite,
    record_identity_link,
)
from codex_ticket_dashboard.lifecycle.contracts import LifecyclePayload
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.models import (
    ProjectChange,
    ProjectionWrite,
    TicketChange,
)

type ReceiptRow = tuple[str, str, int | None, str]
_RECEIPT_ROW: Final[TypeAdapter[ReceiptRow | None]] = TypeAdapter(ReceiptRow | None)


def apply_event(database: Database, command: ApplyCommand) -> bool:  # noqa: C901
    """Append an event, mutate its projection, and mark APPLIED+PENDING atomically."""
    try:
        payload = parse_event_payload(command.event)
    except ValidationError as error:
        raise ProjectionSchemaError from error
    if isinstance(payload, LifecyclePayload):
        return apply_lifecycle(database, command, payload)
    with database.transaction() as connection:
        existing = _RECEIPT_ROW.validate_python(
            connection.execute(
                """SELECT event_id,payload_digest,ingest_seq,state FROM ingest_receipts
                WHERE idempotency_key=?""",
                (command.event.idempotency_key,),
            ).fetchone()
        )
        if existing is not None:
            if str(existing[1]) != command.event.payload_digest:
                raise IdempotencyCollisionError(command.event.event_id)
            if str(existing[3]) == "APPLIED":
                if existing[2] is None:
                    message = "APPLIED_RECEIPT_SEQUENCE_REQUIRED"
                    raise sqlite3.DatabaseError(message)
                return False
        ingest_seq = next_ingest_sequence(connection)
        project_first = _project_before_event(payload)
        if project_first:
            _project(connection, database, command, payload, ingest_seq)
        _ = connection.execute(
            """INSERT INTO ticket_events(
            event_id,idempotency_key,payload_digest,event_type,schema_version,occurred_at,
            received_at,actor_type,origin,authority,project_observation_id,project_id,
            project_resolution_state,repo_key,session_id,turn_id,ticket_id,work_item_id,
            causation_event_id,depends_on_event_ids_json,payload_json,ingest_seq
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                command.event.event_id,
                command.event.idempotency_key,
                command.event.payload_digest,
                command.event.event_type.value,
                command.event.schema_version,
                command.event.occurred_at.isoformat(),
                command.event.received_at.isoformat() if command.event.received_at else None,
                command.event.actor_type.value,
                command.event.origin.value,
                payload.authority.value,
                command.event.project_observation_id,
                command.event.project_id,
                command.event.project_resolution_state.value,
                command.event.repo_key,
                command.event.session_id,
                command.event.turn_id,
                command.event.ticket_id,
                command.event.work_item_id,
                command.event.causation_event_id,
                json.dumps(list(command.event.depends_on_event_ids), separators=(",", ":")),
                canonical_payload_json(payload),
                ingest_seq,
            ),
        )
        project_continuation(connection, command.event, ingest_seq)
        if not project_first:
            _project(connection, database, command, payload, ingest_seq)
        if command.identity_link is not None and command.effective_project_id is not None:
            record_identity_link(
                connection,
                IdentityLinkWrite(
                    command.event,
                    command.effective_project_id,
                    command.identity_link,
                    ingest_seq,
                ),
            )
        if existing is None:
            _ = connection.execute(
                """INSERT INTO ingest_receipts(
                idempotency_key,event_id,payload_digest,state,ingest_seq,archive_state,
                archive_payload_sha256) VALUES (?,?,?,'APPLIED',?,'PENDING',?)""",
                (
                    command.event.idempotency_key,
                    command.event.event_id,
                    command.event.payload_digest,
                    ingest_seq,
                    command.archive_payload_sha256,
                ),
            )
        else:
            _ = connection.execute(
                """UPDATE ingest_receipts SET state='APPLIED',ingest_seq=?,failure_code=NULL,
                failed_dependency_event_id=NULL,root_failed_dependency_event_id=NULL,
                archive_state='PENDING',archive_error_code=NULL,archive_payload_sha256=?
                WHERE idempotency_key=?""",
                (ingest_seq, command.archive_payload_sha256, command.event.idempotency_key),
            )
        _ = connection.execute(
            "DELETE FROM pending_dependencies WHERE event_id=?", (command.event.event_id,)
        )
        persist_mcp_witness(connection, command.event)
        refresh_activity_links(connection, ingest_seq)
        return True


def _project(  # noqa: C901, PLR0912
    connection: sqlite3.Connection,
    database: Database,
    command: ApplyCommand,
    payload: ParsedPayload,
    ingest_seq: int,
) -> None:
    project_id = command.effective_project_id
    match payload:
        case ProjectPayload() as project:
            if project_id is None:
                raise ProjectionSchemaError
            database.write_projection(
                connection,
                ProjectionWrite(
                    ingest_seq,
                    command.event.occurred_at,
                    ProjectChange(
                        project_id=project_id,
                        label=project.label,
                        logical_root_key=project.logical_root_key,
                        repo_key=project.repo_key,
                        identity_source="REGISTRY",
                        identity_source_hash=project.identity_source_hash,
                    ),
                ),
            )
        case TicketPayload() as ticket:
            if project_id is None or command.event.ticket_id is None:
                raise ProjectionSchemaError
            database.write_projection(
                connection,
                ProjectionWrite(
                    ingest_seq,
                    command.event.occurred_at,
                    TicketChange(
                        ticket_id=command.event.ticket_id,
                        project_id=project_id,
                        title=ticket.title,
                        record_type=ticket.record_type,
                        status=ticket.status,
                        needs_triage=ticket.needs_triage,
                        summary=ticket.summary,
                        next_step=ticket.next_step,
                    ),
                ),
            )
        case (WorkItemPayload() | UnclassifiedActivityPayload()) as work_item:
            if command.event.ticket_id is None or command.event.work_item_id is None:
                raise ProjectionSchemaError
            if (
                command.event.event_type is EventType.WORK_ITEM_UPDATED
                and isinstance(work_item, WorkItemPayload)
                and work_item.status in {WorkItemStatus.CANCELLED, WorkItemStatus.SUPERSEDED}
            ):
                decision = command.authority_seam.consume_work_item_decision(
                    connection,
                    WorkItemDecisionConsumptionRequest(command.event, work_item, ingest_seq),
                )
                match decision:
                    case WorkItemDecisionApproved():
                        pass
                    case WorkItemDecisionRejected():
                        raise ProjectionSchemaError(decision.code, "payload.user_decision_event_id")
                    case unreachable:
                        assert_never(unreachable)
            project_work_item(
                connection,
                command.event.ticket_id,
                command.event.work_item_id,
                work_item,
                ingest_seq,
            )
        case TicketLinkPayload():
            if project_id is None or command.event.ticket_id is None:
                raise ProjectionSchemaError
            if not project_ticket_link(
                connection,
                command.event.session_id,
                project_id,
                command.event.ticket_id,
                command.event.occurred_at,
            ):
                raise ProjectionSchemaError
        case PayloadModel():
            require_authority(
                authority.project_authority_payload(
                    connection,
                    command.event,
                    payload,
                    ingest_seq,
                    project_id,
                    command.authority_seam,
                )
            )
        case LifecyclePayload():
            raise ProjectionSchemaError
        case unreachable:
            assert_never(unreachable)


def _project_before_event(payload: ParsedPayload) -> bool:
    return isinstance(payload, ProjectPayload)
