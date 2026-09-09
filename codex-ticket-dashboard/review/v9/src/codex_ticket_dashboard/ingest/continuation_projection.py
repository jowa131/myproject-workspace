"""Atomic single-use continuation and same-ticket directed review relation projection."""

import sqlite3
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.ingest.authority_models import ProjectionSchemaError
from codex_ticket_dashboard.ingest.dead_letter import CollectedEvent
from codex_ticket_dashboard.storage.causation_queries import applied_claim, original_identity

_CLAIM: Final[TypeAdapter[tuple[str] | None]] = TypeAdapter(tuple[str] | None)


def project_continuation(
    connection: sqlite3.Connection, event: CollectedEvent, sequence: int
) -> None:
    """Never infer a relation from a new turn or allow it to bypass user-decision checks."""
    if event.causation_event_id is None:
        return
    source = applied_claim(connection, event.causation_event_id)
    if source is None:
        return
    witness = event.mcp_context
    original = original_identity(connection, source)
    if (
        witness is None
        or original is None
        or source.state in {"NOT_CONTINUED", "UNVERIFIED"}
        or event.causation_event_id not in event.depends_on_event_ids
        or (witness.source_host, witness.thread_id, witness.parent_thread_id)
        != (source.source_host, source.thread_id, original.parent_thread_id)
        or (event.project_observation_id, event.project_id, event.ticket_id)
        != (source.project_observation_id, source.project_id, original.ticket_id)
        or source.continuation_turn_id not in {None, witness.turn_id}
    ):
        raise ProjectionSchemaError
    if witness.turn_id == source.original_turn_id:
        return
    competing = _CLAIM.validate_python(
        connection.execute(
            """SELECT claim_key FROM lifecycle_stop_claims WHERE source_host=? AND thread_id=?
        AND continuation_turn_id=? AND claim_key!=?""",
            (witness.source_host, witness.thread_id, witness.turn_id, source.claim_key),
        ).fetchone()
    )
    if competing is not None:
        raise ProjectionSchemaError
    if source.continuation_turn_id is None:
        _ = connection.execute(
            """UPDATE lifecycle_stop_claims SET continuation_turn_id=?,
            state='CONTINUATION_OBSERVED',updated_seq=? WHERE claim_key=?""",
            (witness.turn_id, sequence, source.claim_key),
        )
    _ = connection.execute(
        "INSERT OR IGNORE INTO turn_relations VALUES (?,?,?,?,?,'STOP_CONTINUATION')",
        (
            event.event_id,
            original.ticket_id,
            witness.thread_id,
            source.original_turn_id,
            witness.turn_id,
        ),
    )
