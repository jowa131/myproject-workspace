"""Public server-rendering adapter over query models."""

from pathlib import Path
from typing import Final, Literal, final

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from codex_ticket_dashboard.web.activity_pages import (
    ActivityCard,
    activity_page_sizes,
    activity_request,
    next_activity_url,
)
from codex_ticket_dashboard.web.api_models import PageRequest, TicketFilters
from codex_ticket_dashboard.web.page_models import DashboardSummary
from codex_ticket_dashboard.web.queries import QueryNotFoundError, QueryRepository

_TEMPLATES: Final = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
_PAGE: Final = PageRequest(limit=50, cursor=None)


@final
class PageRenderer:
    """Render structured query responses without direct database calls."""

    def __init__(self, repository: QueryRepository) -> None:
        """Bind the only permitted read-model source."""
        self._repository = repository

    def response(
        self, request: Request, view: Literal["projects", "board", "compliance", "issues"]
    ) -> HTMLResponse:
        """Render a non-detail screen family."""
        summary = self._summary()
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="screen.html",
            context={"view": view, "summary": summary, "detail": None, "events": ()},
        )

    def ticket(self, request: Request, ticket_id: str) -> HTMLResponse:
        """Render a ticket detail screen from safe structured fields."""
        try:
            detail = self._repository.ticket_detail(ticket_id)
        except QueryNotFoundError:
            return _TEMPLATES.TemplateResponse(
                request=request,
                name="screen.html",
                context={
                    "view": "ticket-not-found",
                    "summary": self._summary(),
                    "detail": None,
                    "events": (),
                },
                status_code=404,
            )
        events = self._repository.ticket_events(ticket_id, _PAGE).items
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="screen.html",
            context={
                "view": "ticket",
                "summary": self._summary(),
                "detail": detail,
                "events": events,
            },
        )

    def activities(self, request: Request) -> HTMLResponse:
        """Render automatic observations without inferring business-ticket status."""
        try:
            query = activity_request(request)
        except ValidationError:
            return _TEMPLATES.TemplateResponse(
                request=request,
                name="screen.html",
                status_code=422,
                context={
                    "view": "activities",
                    "summary": self._summary(),
                    "activity_error": True,
                    "cards": (),
                    "activity_page": None,
                },
            )
        page = self._repository.activities(query)
        return _TEMPLATES.TemplateResponse(
            request=request,
            name="screen.html",
            context={
                "view": "activities",
                "summary": self._summary(),
                "activity_error": False,
                "activity_page": page,
                "cards": tuple(ActivityCard(item) for item in page.items),
                "activity_query": query,
                "activity_page_sizes": activity_page_sizes(query),
                "next_activity_url": next_activity_url(page, query),
            },
        )

    def _summary(self) -> DashboardSummary:
        projects = self._repository.list_projects(_PAGE)
        tickets = self._repository.list_tickets(_PAGE, TicketFilters(None, None, None))
        gates = self._repository.list_compliance(_PAGE)
        issues = self._repository.list_issues(_PAGE)
        return DashboardSummary(
            projects.items,
            tickets.items,
            gates.items,
            issues.items,
            tickets.snapshot_high_watermark,
        )
