"""Observation-only atomic collector projection, independent of ticket existence."""

import json
import sqlite3
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.ingest.authority_models import (
    ApplyCommand,
    IdempotencyCollisionError,
    ProjectionSchemaError,
    next_ingest_sequence,
)
from codex_ticket_dashboard.ingest.dead_letter import CollectedEvent
from codex_ticket_dashboard.lifecycle.contracts import LifecyclePayload
from codex_ticket_dashboard.storage.database import Database

_RECEIPT: Final[TypeAdapter[tuple[str, str] | None]] = TypeAdapter(tuple[str, str] | None)
_PARENT: Final[TypeAdapter[tuple[str | None] | None]] = TypeAdapter(tuple[str | None] | None)


def apply_lifecycle(database: Database, command: ApplyCommand, payload: LifecyclePayload) -> bool:
    """Commit observation, sequence, exact links and archive receipt as one unit."""
    event = command.event
    with database.transaction() as connection:
        existing = _RECEIPT.validate_python(
            connection.execute(
                "SELECT payload_digest,state FROM ingest_receipts WHERE idempotency_key=?",
                (event.idempotency_key,),
            ).fetchone()
        )
        if existing is not None:
            if existing[0] != event.payload_digest:
                raise IdempotencyCollisionError(event.event_id)
            if existing[1] == "APPLIED":
                return False
        sequence = next_ingest_sequence(connection)
        _ = connection.execute(
            """INSERT INTO lifecycle_observations VALUES
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                event.event_id,
                event.idempotency_key,
                event.payload_digest,
                sequence,
                event.occurred_at.isoformat(),
                payload.source_host,
                payload.source_kind,
                payload.source_event_key,
                payload.hook_event,
                event.event_type.value,
                payload.host_session_id,
                payload.thread_id,
                payload.turn_id,
                payload.parent_thread_id,
                payload.relation_state,
                event.project_observation_id,
                event.project_id,
                event.project_resolution_state.value,
                payload.coverage,
                payload.mcp_readiness,
                json.dumps(payload.missing_requirements),
            ),
        )
        if payload.stop_claim is not None:
            claim = payload.stop_claim
            _ = connection.execute(
                """INSERT INTO lifecycle_stop_claims VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(claim_key) DO UPDATE SET
                continuation_turn_id=COALESCE(lifecycle_stop_claims.continuation_turn_id,
                    excluded.continuation_turn_id),
                state=CASE WHEN lifecycle_stop_claims.state='NOT_CONTINUED'
                    OR excluded.state='NOT_CONTINUED' THEN 'NOT_CONTINUED'
                    WHEN lifecycle_stop_claims.state='CONTINUATION_OBSERVED'
                    THEN lifecycle_stop_claims.state ELSE excluded.state END,
                updated_seq=excluded.updated_seq""",
                (
                    claim.claim_key,
                    payload.source_host,
                    payload.thread_id,
                    claim.original_turn_id,
                    event.event_id,
                    claim.continuation_turn_id,
                    claim.state,
                    sequence,
                    sequence,
                ),
            )
        refresh_activity_links(connection, sequence)
        _ = connection.execute(
            """INSERT INTO ingest_receipts(idempotency_key,event_id,payload_digest,state,
            ingest_seq,archive_state,archive_payload_sha256) VALUES (?,?,?,'APPLIED',?,'PENDING',?)
            ON CONFLICT(idempotency_key) DO UPDATE SET state='APPLIED',
            ingest_seq=excluded.ingest_seq,archive_state='PENDING',failure_code=NULL,
            archive_payload_sha256=excluded.archive_payload_sha256""",
            (
                event.idempotency_key,
                event.event_id,
                event.payload_digest,
                sequence,
                command.archive_payload_sha256,
            ),
        )
        _ = connection.execute(
            "DELETE FROM pending_dependencies WHERE event_id=?", (event.event_id,)
        )
    return True


def refresh_activity_links(connection: sqlite3.Connection, sequence: int) -> None:
    """Link either arrival order using exact source observation, thread and own turn."""
    _ = connection.execute(
        """INSERT OR IGNORE INTO lifecycle_activity_links
        SELECT o.event_id,b.event_id,b.ticket_id,? FROM lifecycle_observations o
        JOIN ticket_events b ON b.project_observation_id=o.project_observation_id
            AND b.session_id=o.thread_id AND b.turn_id=o.turn_id
        JOIN lifecycle_mcp_contexts m ON m.event_id=b.event_id
            AND m.source_host=o.source_host AND m.thread_id=o.thread_id
            AND m.turn_id=o.turn_id AND (m.parent_thread_id IS o.parent_thread_id
                OR (o.parent_thread_id IS NULL AND o.relation_state='UNVERIFIED'))
        JOIN tickets t ON t.id=b.ticket_id
        WHERE b.origin='MCP_TOOL' AND o.relation_state!='CONFLICT'
            AND NOT EXISTS (SELECT 1 FROM lifecycle_observations other
                WHERE other.project_observation_id=o.project_observation_id
                AND other.source_host!=o.source_host)
            AND t.project_id=COALESCE(o.project_id,
                (SELECT r.resolved_project_id FROM event_project_resolutions r
                 WHERE r.project_observation_id=o.project_observation_id LIMIT 1))""",
        (sequence,),
    )


def persist_mcp_witness(connection: sqlite3.Connection, event: CollectedEvent) -> None:
    """Persist transport provenance only inside the accepted business event transaction."""
    witness = event.mcp_context
    if witness is not None:
        previous = _PARENT.validate_python(
            connection.execute(
                """SELECT parent_thread_id FROM lifecycle_mcp_contexts
            WHERE source_host=? AND thread_id=? AND turn_id=? LIMIT 1""",
                (witness.source_host, witness.thread_id, witness.turn_id),
            ).fetchone()
        )
        if previous is not None and previous[0] != witness.parent_thread_id:
            raise ProjectionSchemaError
        _ = connection.execute(
            "INSERT INTO lifecycle_mcp_contexts VALUES (?,?,?,?,?)",
            (
                event.event_id,
                witness.source_host,
                witness.thread_id,
                witness.turn_id,
                witness.parent_thread_id,
            ),
        )
