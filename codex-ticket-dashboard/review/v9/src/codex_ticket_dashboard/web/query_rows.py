"""Typed row conversion and response mapping for read-only SQLite queries."""

import sqlite3
from dataclasses import dataclass
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.web.api_models import (
    ComplianceGate,
    IngestIssue,
    Page,
    ProjectItem,
    TicketEvent,
    TicketItem,
    WorkItem,
)
from codex_ticket_dashboard.web.cursors import (
    CursorContext,
    CursorPosition,
    decode_cursor,
    encode_cursor,
    filter_digest,
)

type ProjectRow = tuple[str, str, str, int]
type TicketRow = tuple[str, str, str, str, str, int, str, str, int]
type EventRow = tuple[str, str, str, str, str, str | None, str, str | None, int]
type GateRow = tuple[str, str, str | None, str | None, str, str, str, int]
type IssueRow = tuple[str, str | None, str, str, str, int]
type WorkItemRow = tuple[str, str | None, str, str, str, int]


@dataclass(frozen=True, slots=True)
class PageState:
    """Hold immutable pagination context for one response page."""

    limit: int
    context: CursorContext
    watermark: int


_PROJECT_ROWS: Final = TypeAdapter(list[ProjectRow])
_TICKET_ROWS: Final = TypeAdapter(list[TicketRow])
_EVENT_ROWS: Final = TypeAdapter(list[EventRow])
_GATE_ROWS: Final = TypeAdapter(list[GateRow])
_ISSUE_ROWS: Final = TypeAdapter(list[IssueRow])
_WORK_ITEM_ROWS: Final = TypeAdapter(list[WorkItemRow])
_TEXT_ROWS: Final = TypeAdapter(list[tuple[str]])
_INT_ROWS: Final = TypeAdapter(list[tuple[int]])


type SqlParameter = str | int | None


def int_row(
    connection: sqlite3.Connection, query: str, parameters: tuple[SqlParameter, ...]
) -> int | None:
    """Read a one-integer SQLite result at the storage boundary."""
    rows = _INT_ROWS.validate_python(connection.execute(query, parameters).fetchall())
    return None if not rows else rows[0][0]


def project_rows(
    connection: sqlite3.Connection, query: str, parameters: tuple[SqlParameter, ...]
) -> list[ProjectRow]:
    """Read and validate project list rows."""
    return _PROJECT_ROWS.validate_python(connection.execute(query, parameters).fetchall())


def ticket_rows(
    connection: sqlite3.Connection, query: str, parameters: tuple[SqlParameter, ...]
) -> list[TicketRow]:
    """Read and validate ticket list rows."""
    return _TICKET_ROWS.validate_python(connection.execute(query, parameters).fetchall())


def event_rows(
    connection: sqlite3.Connection, query: str, parameters: tuple[SqlParameter, ...]
) -> list[EventRow]:
    """Read and validate ticket-event list rows."""
    return _EVENT_ROWS.validate_python(connection.execute(query, parameters).fetchall())


def gate_rows(
    connection: sqlite3.Connection, query: str, parameters: tuple[SqlParameter, ...]
) -> list[GateRow]:
    """Read and validate compliance-gate rows."""
    return _GATE_ROWS.validate_python(connection.execute(query, parameters).fetchall())


def issue_rows(
    connection: sqlite3.Connection, query: str, parameters: tuple[SqlParameter, ...]
) -> list[IssueRow]:
    """Read and validate ingest-issue rows."""
    return _ISSUE_ROWS.validate_python(connection.execute(query, parameters).fetchall())


def work_item_rows(connection: sqlite3.Connection, ticket_id: str) -> list[WorkItemRow]:
    """Read current work items for one ticket."""
    return _WORK_ITEM_ROWS.validate_python(
        connection.execute(
            """SELECT id,parent_work_item_id,kind,status,summary,created_seq
            FROM work_items WHERE ticket_id=? ORDER BY created_seq,id""",
            (ticket_id,),
        ).fetchall()
    )


def session_ids(connection: sqlite3.Connection, ticket_id: str) -> tuple[str, ...]:
    """Read linked session identifiers without loading thread contents."""
    rows = _TEXT_ROWS.validate_python(
        connection.execute(
            "SELECT session_id FROM ticket_threads WHERE ticket_id=? ORDER BY session_id",
            (ticket_id,),
        ).fetchall()
    )
    return tuple(row[0] for row in rows)


def ticket_item(row: TicketRow) -> TicketItem:
    """Map a validated ticket row to its response model."""
    return TicketItem(
        ticket_id=row[0],
        project_id=row[1],
        title=row[2],
        record_type=row[3],
        status=row[4],
        needs_triage=bool(row[5]),
        summary=row[6],
        next_step=row[7],
        created_seq=row[8],
    )


def work_item(row: WorkItemRow) -> WorkItem:
    """Map a validated work-item row to its response model."""
    return WorkItem(
        work_item_id=row[0],
        parent_work_item_id=row[1],
        kind=row[2],
        status=row[3],
        summary=row[4],
        created_seq=row[5],
    )


def gate(row: GateRow) -> ComplianceGate:
    """Map a validated compliance-gate row to its response model."""
    return ComplianceGate(
        gate_id=row[0],
        project_id=row[1],
        ticket_id=row[2],
        work_item_id=row[3],
        gate_type=row[4],
        requirement=row[5],
        status=row[6],
        created_seq=row[7],
    )


def event(row: EventRow) -> TicketEvent:
    """Map a validated event row without payload fields."""
    return TicketEvent(
        event_id=row[0],
        event_type=row[1],
        occurred_at=row[2],
        actor_type=row[3],
        authority=row[4],
        project_id=row[5],
        ticket_id=row[6],
        work_item_id=row[7],
        ingest_seq=row[8],
    )


def issue(row: IssueRow) -> IngestIssue:
    """Map a validated ingest-issue row to its response model."""
    return IngestIssue(
        issue_id=row[0],
        event_id=row[1],
        code=row[2],
        field_path=row[3],
        state=row[4],
        created_seq=row[5],
    )


def page_parameters(
    watermark: int, position: CursorPosition | None, limit: int
) -> tuple[int | str | None, ...]:
    """Build parameterized as-of list query bindings."""
    return (watermark, watermark, *page_tail(position, limit))


def page_tail(position: CursorPosition | None, limit: int) -> tuple[int | str | None, ...]:
    """Build keyset position bindings without interpolating SQL."""
    if position is None:
        return (None, None, None, None, limit + 1)
    return (position.sequence, position.sequence, position.sequence, position.stable_id, limit + 1)


def page_response[Item: ProjectItem | TicketItem | TicketEvent | ComplianceGate | IngestIssue](
    items: tuple[Item, ...], row_count: int, state: PageState, last: tuple[int, str] | None
) -> Page[Item]:
    """Return an opaque next cursor only when another immutable row exists."""
    has_more = row_count > state.limit
    if not has_more:
        return Page[Item](
            items=items,
            next_cursor=None,
            has_more=False,
            snapshot_high_watermark=state.watermark,
        )
    if last is None:
        raise AssertionError
    return Page[Item](
        items=items,
        next_cursor=encode_cursor(state.context, CursorPosition(*last, state.watermark)),
        has_more=True,
        snapshot_high_watermark=state.watermark,
    )


def ticket_filter_values(
    status: str | None, project_id: str | None, needs_triage: bool | None
) -> tuple[tuple[str, str], ...]:
    """Normalize ticket filters before their digest enters a cursor."""
    return (
        ("needs_triage", "" if needs_triage is None else str(needs_triage).lower()),
        ("project_id", project_id or ""),
        ("status", status or ""),
    )


def ticket_gates(connection: sqlite3.Connection, ticket_id: str, watermark: int) -> list[GateRow]:
    """Read as-of compliance gates for one ticket detail response."""
    return gate_rows(
        connection,
        """SELECT gate_id,project_id,ticket_id,work_item_id,gate_type,requirement,status,
        created_seq FROM compliance_gate_versions WHERE ticket_id=? AND valid_from_ingest_seq<=?
        AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?) ORDER BY created_seq,gate_id""",
        (ticket_id, watermark, watermark),
    )


def page_context(
    route_id: str, filters: tuple[tuple[str, str], ...], cursor: str | None
) -> tuple[CursorContext, CursorPosition | None]:
    """Bind a supplied cursor to its exact route and normalized filters."""
    context = CursorContext(route_id=route_id, filter_digest=filter_digest(filters))
    return context, None if cursor is None else decode_cursor(cursor, context)


def snapshot_watermark(current: int, position: CursorPosition | None) -> int | None:
    """Return a cursor watermark only when it is not newer than the database."""
    if position is None:
        return current
    if position.snapshot_high_watermark > current:
        return None
    return position.snapshot_high_watermark
