"""Connected source-turn authority checks."""

import sqlite3
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.ingest.authority_models import ConnectedTurnRequest

_RELATION_ROW: Final[TypeAdapter[tuple[int] | None]] = TypeAdapter(tuple[int] | None)


def is_connected_source_turn(
    connection: sqlite3.Connection,
    request: ConnectedTurnRequest,
) -> bool:
    """Accept identity or one explicitly applied directed turn relation."""
    if request.source_turn_id == request.related_turn_id:
        return True
    row = _RELATION_ROW.validate_python(
        connection.execute(
            """SELECT 1 FROM turn_relations
            WHERE ticket_id=? AND session_id=? AND source_turn_id=? AND related_turn_id=?
            AND relation_type IN ('USER_FOLLOWUP','STOP_CONTINUATION','REOPEN_FOLLOWUP')""",
            (
                request.ticket_id,
                request.session_id,
                request.source_turn_id,
                request.related_turn_id,
            ),
        ).fetchone()
    )
    return row is not None
