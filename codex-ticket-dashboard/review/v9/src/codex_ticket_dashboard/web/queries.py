"""Read-only SQLite projections for every HTTP route."""

import sqlite3
from typing import Literal

from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.lifecycle_queries import (
    ActivityPage,
    ActivityPageRequest,
    LifecycleQueries,
)
from codex_ticket_dashboard.web.api_models import (
    ComplianceGate,
    HealthResponse,
    IngestIssue,
    Page,
    PageRequest,
    ProjectDetail,
    ProjectItem,
    TicketDetail,
    TicketEvent,
    TicketFilters,
    TicketItem,
)
from codex_ticket_dashboard.web.cursors import CursorPosition
from codex_ticket_dashboard.web.query_rows import (
    PageState,
    event,
    event_rows,
    gate,
    gate_rows,
    int_row,
    issue,
    issue_rows,
    page_context,
    page_parameters,
    page_response,
    page_tail,
    project_rows,
    session_ids,
    snapshot_watermark,
    ticket_filter_values,
    ticket_gates,
    ticket_item,
    ticket_rows,
    work_item,
    work_item_rows,
)


class SnapshotUnavailableError(LookupError):
    """Report missing as-of projection history without partial results."""

    code: Literal["SNAPSHOT_UNAVAILABLE"] = "SNAPSHOT_UNAVAILABLE"


class QueryNotFoundError(LookupError):
    """Report a current projection that cannot be found."""

    code: Literal["NOT_FOUND"] = "NOT_FOUND"


class QueryRepository:
    """Read projections through SQLite query-only transactions only."""

    _database: Database

    def __init__(self, database: Database) -> None:
        """Bind all query operations to one database configuration."""
        self._database = database

    def health(self) -> HealthResponse:
        """Return the current projection sequence without collector mutation."""
        with self._database.read_transaction() as connection:
            return HealthResponse(snapshot_high_watermark=_watermark(connection))

    def activities(self, page: ActivityPageRequest) -> ActivityPage:
        """Read unresolved and linked activity through the snapshot query contract."""
        return LifecycleQueries(self._database).activities(page)

    def list_projects(self, page: PageRequest) -> Page[ProjectItem]:
        """List projects by immutable creation sequence."""
        context, position = page_context("projects", (), page.cursor)
        with self._database.read_transaction() as connection:
            watermark = _snapshot_watermark(connection, position)
            rows = project_rows(
                connection,
                """SELECT project_id,label,repo_key,created_seq FROM project_versions
                WHERE valid_from_ingest_seq<=?
                AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)
                AND (? IS NULL OR created_seq>? OR (created_seq=? AND project_id>?))
                ORDER BY created_seq,project_id LIMIT ?""",
                page_parameters(watermark, position, page.limit),
            )
        items = tuple(
            ProjectItem(project_id=row[0], label=row[1], repo_key=row[2], created_seq=row[3])
            for row in rows[: page.limit]
        )
        last = (
            None if len(rows) <= page.limit else (rows[page.limit - 1][3], rows[page.limit - 1][0])
        )
        return page_response(items, len(rows), PageState(page.limit, context, watermark), last)

    def project_detail(self, project_id: str) -> ProjectDetail:
        """Load one project and its current as-of gate count."""
        with self._database.read_transaction() as connection:
            watermark = _watermark(connection)
            row = project_rows(
                connection,
                """SELECT project_id,label,repo_key,created_seq
                FROM project_versions WHERE project_id=?
                AND valid_from_ingest_seq<=?
                AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)""",
                (project_id, watermark, watermark),
            )
            count = int_row(
                connection,
                """SELECT COUNT(*) FROM compliance_gate_versions WHERE project_id=?
                AND valid_from_ingest_seq<=?
                AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)""",
                (project_id, watermark, watermark),
            )
        if not row or count is None:
            raise QueryNotFoundError
        project = row[0]
        return ProjectDetail(
            project_id=project[0],
            label=project[1],
            repo_key=project[2],
            created_seq=project[3],
            compliance_gate_count=count,
        )

    def list_tickets(self, page: PageRequest, filters: TicketFilters) -> Page[TicketItem]:
        """List filtered ticket projections by immutable creation sequence."""
        context, position = page_context(
            "tickets",
            ticket_filter_values(filters.status, filters.project_id, filters.needs_triage),
            page.cursor,
        )
        status = filters.status
        project_id = filters.project_id
        triage = None if filters.needs_triage is None else int(filters.needs_triage)
        with self._database.read_transaction() as connection:
            watermark = _snapshot_watermark(connection, position)
            rows = ticket_rows(
                connection,
                """SELECT ticket_id,project_id,title,record_type,status,needs_triage,summary,
                next_step,created_seq FROM ticket_versions WHERE valid_from_ingest_seq<=?
                AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)
                AND (? IS NULL OR status=?) AND (? IS NULL OR project_id=?)
                AND (? IS NULL OR needs_triage=?)
                AND (? IS NULL OR created_seq>? OR (created_seq=? AND ticket_id>?))
                ORDER BY created_seq,ticket_id LIMIT ?""",
                (
                    watermark,
                    watermark,
                    status,
                    status,
                    project_id,
                    project_id,
                    triage,
                    triage,
                    *page_tail(position, page.limit),
                ),
            )
        items = tuple(ticket_item(row) for row in rows[: page.limit])
        last = (
            None if len(rows) <= page.limit else (rows[page.limit - 1][8], rows[page.limit - 1][0])
        )
        return page_response(items, len(rows), PageState(page.limit, context, watermark), last)

    def ticket_detail(self, ticket_id: str) -> TicketDetail:
        """Load current structured ticket, relation, work-item, and gate state."""
        with self._database.read_transaction() as connection:
            watermark = _watermark(connection)
            rows = ticket_rows(
                connection,
                """SELECT ticket_id,project_id,title,record_type,status,needs_triage,summary,
                next_step,created_seq FROM ticket_versions WHERE ticket_id=?
                AND valid_from_ingest_seq<=?
                AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)""",
                (ticket_id, watermark, watermark),
            )
            sessions = session_ids(connection, ticket_id)
            work_items = work_item_rows(connection, ticket_id)
            gates = ticket_gates(connection, ticket_id, watermark)
        if not rows:
            raise QueryNotFoundError
        ticket = ticket_item(rows[0])
        return TicketDetail(
            ticket_id=ticket.ticket_id,
            project_id=ticket.project_id,
            title=ticket.title,
            record_type=ticket.record_type,
            status=ticket.status,
            needs_triage=ticket.needs_triage,
            summary=ticket.summary,
            next_step=ticket.next_step,
            created_seq=ticket.created_seq,
            session_ids=sessions,
            work_items=tuple(work_item(row) for row in work_items),
            compliance_gates=tuple(gate(row) for row in gates),
        )

    def ticket_events(self, ticket_id: str, page: PageRequest) -> Page[TicketEvent]:
        """List exact ticket-scoped immutable event metadata by ingest sequence."""
        context, position = page_context("ticket-events", (("ticket_id", ticket_id),), page.cursor)
        with self._database.read_transaction() as connection:
            watermark = _snapshot_watermark(connection, position)
            rows = event_rows(
                connection,
                """SELECT event_id,event_type,occurred_at,actor_type,authority,project_id,ticket_id,
                work_item_id,ingest_seq FROM ticket_events WHERE ticket_id=? AND ingest_seq<=?
                AND (? IS NULL OR ingest_seq>? OR (ingest_seq=? AND event_id>?))
                ORDER BY ingest_seq,event_id LIMIT ?""",
                (ticket_id, watermark, *page_tail(position, page.limit)),
            )
        items = tuple(event(row) for row in rows[: page.limit])
        last = (
            None if len(rows) <= page.limit else (rows[page.limit - 1][8], rows[page.limit - 1][0])
        )
        return page_response(items, len(rows), PageState(page.limit, context, watermark), last)

    def list_compliance(self, page: PageRequest) -> Page[ComplianceGate]:
        """List compliance gates by their immutable creation sequence."""
        return self._list_gates(page, None)

    def list_issues(self, page: PageRequest) -> Page[IngestIssue]:
        """List collector issues by immutable creation sequence."""
        context, position = page_context("ingest-issues", (), page.cursor)
        with self._database.read_transaction() as connection:
            watermark = _snapshot_watermark(connection, position)
            rows = issue_rows(
                connection,
                """SELECT issue_id,event_id,code,field_path,state,created_seq
                FROM ingest_issue_versions
                WHERE valid_from_ingest_seq<=?
                AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)
                AND (? IS NULL OR created_seq>? OR (created_seq=? AND issue_id>?))
                ORDER BY created_seq,issue_id LIMIT ?""",
                page_parameters(watermark, position, page.limit),
            )
        items = tuple(issue(row) for row in rows[: page.limit])
        last = (
            None if len(rows) <= page.limit else (rows[page.limit - 1][5], rows[page.limit - 1][0])
        )
        return page_response(items, len(rows), PageState(page.limit, context, watermark), last)

    def _list_gates(self, page: PageRequest, ticket_id: str | None) -> Page[ComplianceGate]:
        context, position = page_context("compliance", (), page.cursor)
        with self._database.read_transaction() as connection:
            watermark = _snapshot_watermark(connection, position)
            rows = gate_rows(
                connection,
                """SELECT gate_id,project_id,ticket_id,work_item_id,gate_type,requirement,status,
                created_seq FROM compliance_gate_versions WHERE valid_from_ingest_seq<=?
                AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)
                AND (? IS NULL OR ticket_id=?)
                AND (? IS NULL OR created_seq>? OR (created_seq=? AND gate_id>?))
                ORDER BY created_seq,gate_id LIMIT ?""",
                (watermark, watermark, ticket_id, ticket_id, *page_tail(position, page.limit)),
            )
        items = tuple(gate(row) for row in rows[: page.limit])
        last = (
            None if len(rows) <= page.limit else (rows[page.limit - 1][7], rows[page.limit - 1][0])
        )
        return page_response(items, len(rows), PageState(page.limit, context, watermark), last)


def _watermark(connection: sqlite3.Connection) -> int:
    value = int_row(connection, "SELECT last_seq FROM ingest_sequences WHERE singleton=1", ())
    if value is None:
        raise SnapshotUnavailableError
    return value


def _snapshot_watermark(connection: sqlite3.Connection, position: CursorPosition | None) -> int:
    watermark = snapshot_watermark(_watermark(connection), position)
    if watermark is None:
        raise SnapshotUnavailableError
    return watermark
