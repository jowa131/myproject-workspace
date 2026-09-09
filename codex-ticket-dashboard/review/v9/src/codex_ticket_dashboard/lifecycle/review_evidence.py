"""Reuse collector review validation as a read-only proof, never a state mutation."""

import sqlite3
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.domain.events import EventEnvelope
from codex_ticket_dashboard.domain.status import TicketStatus
from codex_ticket_dashboard.ingest.authority_models import AuthorityApproved, ReviewAdmissionRequest
from codex_ticket_dashboard.ingest.dead_letter import JsonPayload
from codex_ticket_dashboard.ingest.payload_models import StatusPayload
from codex_ticket_dashboard.ingest.review_invalidation import validate_in_review_admission
from codex_ticket_dashboard.storage.turn_recording import TurnRecording

_TEXT: Final[TypeAdapter[tuple[str | None] | None]] = TypeAdapter(tuple[str | None] | None)
_STATUS: Final[TypeAdapter[tuple[str, str, int] | None]] = TypeAdapter(tuple[str, str, int] | None)
_EVENT_JSON: Final = """SELECT json_object(
'schema_version',schema_version,'event_id',event_id,'event_type',event_type,
'occurred_at',occurred_at,'received_at',received_at,'actor_type',actor_type,'origin',origin,
'project_observation_id',project_observation_id,'project_id',project_id,
'project_resolution_state',project_resolution_state,'repo_key',repo_key,
'session_id',session_id,'turn_id',turn_id,'ticket_id',ticket_id,'work_item_id',work_item_id,
'causation_event_id',causation_event_id,'depends_on_event_ids',json(depends_on_event_ids_json),
'payload',json(payload_json),'idempotency_key',idempotency_key,'payload_digest',payload_digest),
payload_json,ingest_seq FROM ticket_events WHERE event_id=? AND ingest_seq<=?"""


def review_is_verified(
    connection: sqlite3.Connection,
    recording: TurnRecording,
    watermark: int,
) -> bool:
    """Require exact active work-item/gate/dependency closure for a claimed IN_REVIEW."""
    summaries = [fact for fact in recording.facts if fact.event_type == "TURN_SUMMARIZED"]
    if not summaries:
        return True
    proposed = _TEXT.validate_python(
        connection.execute(
            """SELECT json_extract(payload_json,'$.proposed_status')
            FROM ticket_events WHERE event_id=?""",
            (summaries[-1].event_id,),
        ).fetchone()
    )
    if proposed is None or proposed[0] is None:
        return False
    status = TicketStatus(proposed[0])
    if status != TicketStatus.IN_REVIEW:
        return status not in {TicketStatus.COMPLETED, TicketStatus.CANCELLED}
    candidates = [fact for fact in reversed(recording.facts) if fact.event_type == "STATUS_CHANGED"]
    for fact in candidates:
        row = _STATUS.validate_python(
            connection.execute(_EVENT_JSON, (fact.event_id, watermark)).fetchone()
        )
        if row is None:
            return False
        payload = StatusPayload.model_validate_json(row[1])
        if payload.to_status != TicketStatus.IN_REVIEW:
            continue
        event = EventEnvelope[JsonPayload].model_validate_json(row[0])
        result = validate_in_review_admission(
            connection, ReviewAdmissionRequest(event, payload, row[2])
        )
        return isinstance(result, AuthorityApproved)
    return False
