"""Read original and explicitly bound correction facts without rewriting either turn."""

import sqlite3
from dataclasses import dataclass, replace
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.storage.turn_recording import (
    TurnKey,
    TurnRecording,
    read_turn_recording,
)


@dataclass(frozen=True, slots=True)
class RelatedRecording:
    """Separate original/correction records with an explicit accepted claim reference."""

    original_key: TurnKey
    original: TurnRecording
    correction_key: TurnKey | None = None
    correction: TurnRecording | None = None
    claim_event_id: str | None = None
    relation_unverified: bool = False

    @property
    def combined(self) -> TurnRecording:
        """Combine only verified related evidence for policy assessment, never ticket closure."""
        if self.correction is None:
            return self.original
        facts = tuple(
            sorted(
                (*self.original.facts, *self.correction.facts),
                key=lambda fact: (fact.ingest_seq, fact.event_id),
            )
        )
        return TurnRecording(facts, (), "RECORDED" if facts else "UNVERIFIED")


_ROWS: Final = TypeAdapter(list[tuple[str, str, str | None, str, int, int | None]])


def read_related_recording(
    connection: sqlite3.Connection,
    key: TurnKey,
    high_watermark: int,
) -> RelatedRecording:
    """Read explicit claim and directed relation evidence at its immutable binding sequence."""
    own = read_turn_recording(connection, key, high_watermark)
    rows = _ROWS.validate_python(
        connection.execute(
            """SELECT c.claim_event_id,c.original_turn_id,c.continuation_turn_id,
        c.state,c.updated_seq,
        (SELECT MIN(b.ingest_seq) FROM turn_relations r
         JOIN ticket_events b ON b.event_id=r.relation_event_id
         JOIN lifecycle_mcp_contexts m ON m.event_id=b.event_id AND m.source_host=c.source_host
         WHERE r.session_id=c.thread_id AND r.source_turn_id=c.original_turn_id
         AND r.related_turn_id=c.continuation_turn_id AND r.relation_type='STOP_CONTINUATION')
        FROM lifecycle_stop_claims c WHERE c.source_host=? AND c.thread_id=?
        AND (c.original_turn_id=? OR c.continuation_turn_id=?) AND c.created_seq<=?""",
            (key.source_host, key.thread_id, key.turn_id, key.turn_id, high_watermark),
        ).fetchall()
    )
    if not rows:
        return RelatedRecording(key, own)
    if len(rows) != 1:
        return RelatedRecording(key, own, relation_unverified=True)
    event_id, original_turn, correction_turn, state, updated, binding = rows[0]
    original_key = replace(key, turn_id=original_turn)
    original = read_turn_recording(connection, original_key, high_watermark)
    if state == "UNVERIFIED" or (correction_turn is not None and binding is None):
        return RelatedRecording(
            original_key, original, claim_event_id=event_id, relation_unverified=True
        )
    if (
        correction_turn is None
        or binding is None
        or binding > high_watermark
        or (state == "NOT_CONTINUED" and updated <= high_watermark)
    ):
        return RelatedRecording(original_key, original, claim_event_id=event_id)
    correction_key = replace(key, turn_id=correction_turn)
    return RelatedRecording(
        original_key,
        original,
        correction_key,
        read_turn_recording(connection, correction_key, high_watermark),
        event_id,
    )
