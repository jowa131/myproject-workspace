"""Exact witnessed turn facts shared by activity queries and bounded Stop checks."""

import sqlite3
from dataclasses import dataclass
from typing import Final, Literal

from pydantic import TypeAdapter

from codex_ticket_dashboard.domain.events import EventType
from codex_ticket_dashboard.lifecycle.contracts import MissingRequirement


@dataclass(frozen=True, slots=True)
class TurnKey:
    """A child owns its turn; parent identity is corroboration, never a turn substitute."""

    source_host: str
    thread_id: str
    turn_id: str
    parent_thread_id: str | None = None


@dataclass(frozen=True, slots=True)
class TurnFact:
    """Applied business identity and machine result only, with no prose."""

    event_id: str
    event_type: str
    ticket_id: str | None
    ingest_seq: int
    result: str | None
    classification: str | None
    disposition: str | None
    declared_git_requirement: str | None
    declared_wiki_requirement: str | None
    resolved_requirement: str | None


@dataclass(frozen=True, slots=True)
class TurnRecording:
    """Positive persisted evidence and explicit gaps, not inferred completion."""

    facts: tuple[TurnFact, ...]
    missing_requirements: tuple[MissingRequirement, ...]
    state: Literal["RECORDED", "MISSING", "UNVERIFIED"]


_ROWS: Final = TypeAdapter(
    list[
        tuple[
            str,
            str,
            str | None,
            int,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
            str | None,
        ]
    ]
)
_REQUIRED: Final[tuple[tuple[MissingRequirement, frozenset[EventType]], ...]] = (
    (
        "PREFLIGHT",
        frozenset(
            {
                EventType.TICKET_CREATED,
                EventType.TICKET_LINKED_TO_THREAD,
                EventType.TICKET_PREFLIGHT_RECORDED,
            }
        ),
    ),
    ("TURN_SUMMARY", frozenset({EventType.TURN_SUMMARIZED})),
    ("GIT_GATE", frozenset({EventType.GIT_GATE_REPORTED})),
    ("WIKI_GATE", frozenset({EventType.WIKI_GATE_REPORTED})),
)


def read_turn_recording(
    connection: sqlite3.Connection,
    key: TurnKey,
    high_watermark: int,
) -> TurnRecording:
    """Read only applied server-witnessed own-turn facts as of one ingest boundary."""
    rows = _ROWS.validate_python(
        connection.execute(
            """SELECT b.event_id,b.event_type,b.ticket_id,b.ingest_seq,
        json_extract(b.payload_json,'$.result'),json_extract(b.payload_json,'$.classification'),
        json_extract(b.payload_json,'$.disposition'),
        json_extract(b.payload_json,'$.declared_git_requirement'),
        json_extract(b.payload_json,'$.declared_wiki_requirement'),
        json_extract(b.payload_json,'$.resolved_requirement')
        FROM ticket_events b JOIN lifecycle_mcp_contexts m ON m.event_id=b.event_id
        WHERE m.source_host=? AND m.thread_id=? AND m.turn_id=?
        AND m.parent_thread_id IS ? AND b.ingest_seq<=? ORDER BY b.ingest_seq,b.event_id""",
            (key.source_host, key.thread_id, key.turn_id, key.parent_thread_id, high_watermark),
        ).fetchall()
    )
    facts = tuple(TurnFact(*row) for row in rows)
    types = {fact.event_type for fact in facts}
    missing: tuple[MissingRequirement, ...] = tuple(
        requirement for requirement, tags in _REQUIRED if not types & tags
    )
    return TurnRecording(
        facts, missing, "UNVERIFIED" if not facts else "MISSING" if missing else "RECORDED"
    )
