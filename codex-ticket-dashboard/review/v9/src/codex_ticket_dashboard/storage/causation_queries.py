"""Exact applied Stop claim and original witnessed ticket identity reads."""

import sqlite3
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, TypeAdapter


class ClaimSource(BaseModel):
    """Accepted source context; current-turn metadata is deliberately absent."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    event_id: str
    claim_key: str
    source_host: str
    thread_id: str
    original_turn_id: str
    continuation_turn_id: str | None
    state: Literal["CLAIMED", "CONTINUATION_OBSERVED", "NOT_CONTINUED", "UNVERIFIED"]
    project_observation_id: str
    project_id: str | None
    repo_key: str | None
    parent_thread_id: str | None


class OriginalIdentity(BaseModel):
    """One original ticket and independently witnessed parent, with no prose."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    ticket_id: str
    parent_thread_id: str | None


type SourceRow = tuple[
    str,
    str,
    str,
    str,
    str,
    str | None,
    str,
    str,
    str | None,
    str | None,
    str | None,
]
_SOURCE: Final[TypeAdapter[SourceRow | None]] = TypeAdapter(SourceRow | None)
_IDENTITIES: Final = TypeAdapter(list[tuple[str, str | None]])
_IDS: Final = TypeAdapter(list[tuple[str]])


def applied_claim(connection: sqlite3.Connection, event_id: str) -> ClaimSource | None:
    """Require the exact claim event's APPLIED receipt, never another Stop by recency."""
    row = _SOURCE.validate_python(
        connection.execute(
            """SELECT c.claim_event_id,c.claim_key,c.source_host,c.thread_id,c.original_turn_id,
        c.continuation_turn_id,c.state,o.project_observation_id,
        COALESCE(o.project_id,r.resolved_project_id),p.repo_key,o.parent_thread_id
        FROM lifecycle_stop_claims c JOIN lifecycle_observations o ON o.event_id=c.claim_event_id
        JOIN ingest_receipts i ON i.event_id=o.event_id AND i.state='APPLIED'
        LEFT JOIN event_project_resolutions r ON r.project_observation_id=o.project_observation_id
        LEFT JOIN projects p ON p.id=COALESCE(o.project_id,r.resolved_project_id)
        WHERE c.claim_event_id=? AND o.event_type='TURN_STOPPED'""",
            (event_id,),
        ).fetchone()
    )
    if row is None:
        return None
    return ClaimSource.model_validate(dict(zip(ClaimSource.model_fields, row, strict=True)))


def original_identity(
    connection: sqlite3.Connection, source: ClaimSource
) -> OriginalIdentity | None:
    """Do not pick a ticket or parent when original witnessed facts disagree."""
    rows = _IDENTITIES.validate_python(
        connection.execute(
            """SELECT DISTINCT b.ticket_id,m.parent_thread_id
        FROM ticket_events b JOIN lifecycle_mcp_contexts m ON m.event_id=b.event_id
        JOIN tickets t ON t.id=b.ticket_id AND t.project_id=?
        WHERE m.source_host=? AND m.thread_id=? AND m.turn_id=?
        AND b.project_observation_id=?""",
            (
                source.project_id,
                source.source_host,
                source.thread_id,
                source.original_turn_id,
                source.project_observation_id,
            ),
        ).fetchall()
    )
    if len(rows) != 1 or (
        source.parent_thread_id is not None and source.parent_thread_id != rows[0][1]
    ):
        return None
    return OriginalIdentity(ticket_id=rows[0][0], parent_thread_id=rows[0][1])


def bound_claim_id(connection: sqlite3.Connection, thread_id: str, turn_id: str) -> str | None:
    """Find a previously verified exact continuation, without choosing among hosts."""
    rows = _IDS.validate_python(
        connection.execute(
            """SELECT claim_event_id FROM lifecycle_stop_claims
        WHERE thread_id=? AND continuation_turn_id=? AND state='CONTINUATION_OBSERVED'""",
            (thread_id, turn_id),
        ).fetchall()
    )
    return rows[0][0] if len(rows) == 1 else None
