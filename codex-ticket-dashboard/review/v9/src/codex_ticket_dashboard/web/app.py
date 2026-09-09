"""Local-only FastAPI application with exactly eight GET and HEAD routes."""

from dataclasses import dataclass
from typing import Annotated, Literal, final

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.web.api_models import (
    ComplianceGate,
    ErrorResponse,
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
from codex_ticket_dashboard.web.cursors import CursorContextMismatchError, InvalidCursorError
from codex_ticket_dashboard.web.queries import (
    QueryNotFoundError,
    QueryRepository,
    SnapshotUnavailableError,
)
from codex_ticket_dashboard.web.security import (
    SecurityConfig,
    apply_security_headers,
    request_rejection_code,
)

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
MAX_FILTER_LENGTH = 160


@final
class QueryInputError(ValueError):
    """Represent a safe client-query validation failure."""

    code: Literal["INVALID_LIMIT", "INVALID_FILTER"]

    def __init__(self, code: Literal["INVALID_LIMIT", "INVALID_FILTER"]) -> None:
        """Keep the response error code fixed at the input boundary."""
        self.code = code
        super().__init__(code)


def create_app(database: Database, *, port: int) -> FastAPI:
    """Build a local read-only API without documentation or mutation routes."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    _install_boundary(app, SecurityConfig(port=port))
    _install_errors(app)
    _install_routes(app, _Routes(QueryRepository(database)))
    return app


def _install_boundary(app: FastAPI, security: SecurityConfig) -> None:
    async def local_boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        rejection = request_rejection_code(request, security)
        if rejection is not None:
            response = _error_response(rejection, 400)
        else:
            try:
                response = await call_next(request)
            except Exception:  # noqa: BLE001  # noqa: BROAD_EXCEPT_OK
                response = _error_response("INTERNAL_ERROR", 500)
        apply_security_headers(response.headers)
        return response

    _ = app.middleware("http")(local_boundary)


def _install_errors(app: FastAPI) -> None:
    async def invalid_input(_: Request, error: QueryInputError) -> JSONResponse:
        return _error_response(error.code, 400)

    _ = app.exception_handler(QueryInputError)(invalid_input)

    async def invalid_cursor(_: Request, error: InvalidCursorError) -> JSONResponse:
        return _error_response(error.code, 400)

    _ = app.exception_handler(InvalidCursorError)(invalid_cursor)

    async def cursor_context(_: Request, error: CursorContextMismatchError) -> JSONResponse:
        return _error_response(error.code, 400)

    _ = app.exception_handler(CursorContextMismatchError)(cursor_context)

    async def unavailable_snapshot(_: Request, error: SnapshotUnavailableError) -> JSONResponse:
        return _error_response(error.code, 409)

    _ = app.exception_handler(SnapshotUnavailableError)(unavailable_snapshot)

    async def not_found(_: Request, error: QueryNotFoundError) -> JSONResponse:
        return _error_response(error.code, 404)

    _ = app.exception_handler(QueryNotFoundError)(not_found)


@dataclass(frozen=True, slots=True)
class _Routes:
    repository: QueryRepository

    async def health(self) -> HealthResponse:
        return self.repository.health()

    async def projects(
        self, limit: Annotated[str, Query()] = "50", cursor: Annotated[str | None, Query()] = None
    ) -> Page[ProjectItem]:
        return self.repository.list_projects(_page_request(limit, cursor))

    async def project(self, project_id: str) -> ProjectDetail:
        return self.repository.project_detail(project_id)

    async def tickets(
        self,
        limit: Annotated[str, Query()] = "50",
        cursor: Annotated[str | None, Query()] = None,
        status: Annotated[str | None, Query()] = None,
        project_id: Annotated[str | None, Query()] = None,
        needs_triage: Annotated[str | None, Query()] = None,
    ) -> Page[TicketItem]:
        return self.repository.list_tickets(
            _page_request(limit, cursor), _ticket_filters(status, project_id, needs_triage)
        )

    async def ticket(self, ticket_id: str) -> TicketDetail:
        return self.repository.ticket_detail(ticket_id)

    async def ticket_events(
        self,
        ticket_id: str,
        limit: Annotated[str, Query()] = "50",
        cursor: Annotated[str | None, Query()] = None,
    ) -> Page[TicketEvent]:
        return self.repository.ticket_events(ticket_id, _page_request(limit, cursor))

    async def compliance(
        self, limit: Annotated[str, Query()] = "50", cursor: Annotated[str | None, Query()] = None
    ) -> Page[ComplianceGate]:
        return self.repository.list_compliance(_page_request(limit, cursor))

    async def ingest_issues(
        self, limit: Annotated[str, Query()] = "50", cursor: Annotated[str | None, Query()] = None
    ) -> Page[IngestIssue]:
        return self.repository.list_issues(_page_request(limit, cursor))


def _install_routes(app: FastAPI, routes: _Routes) -> None:
    app.add_api_route(
        "/api/v1/health", routes.health, methods=["GET", "HEAD"], response_model=HealthResponse
    )
    app.add_api_route(
        "/api/v1/projects",
        routes.projects,
        methods=["GET", "HEAD"],
        response_model=Page[ProjectItem],
    )
    app.add_api_route(
        "/api/v1/projects/{project_id}",
        routes.project,
        methods=["GET", "HEAD"],
        response_model=ProjectDetail,
    )
    app.add_api_route(
        "/api/v1/tickets", routes.tickets, methods=["GET", "HEAD"], response_model=Page[TicketItem]
    )
    app.add_api_route(
        "/api/v1/tickets/{ticket_id}",
        routes.ticket,
        methods=["GET", "HEAD"],
        response_model=TicketDetail,
    )
    app.add_api_route(
        "/api/v1/tickets/{ticket_id}/events",
        routes.ticket_events,
        methods=["GET", "HEAD"],
        response_model=Page[TicketEvent],
    )
    app.add_api_route(
        "/api/v1/compliance",
        routes.compliance,
        methods=["GET", "HEAD"],
        response_model=Page[ComplianceGate],
    )
    app.add_api_route(
        "/api/v1/ingest/issues",
        routes.ingest_issues,
        methods=["GET", "HEAD"],
        response_model=Page[IngestIssue],
    )


def _page_request(limit: str, cursor: str | None) -> PageRequest:
    code: Literal["INVALID_LIMIT"] = "INVALID_LIMIT"
    try:
        parsed = int(limit)
    except ValueError as error:
        raise QueryInputError(code) from error
    if not 1 <= parsed <= MAX_LIMIT:
        raise QueryInputError(code)
    return PageRequest(limit=parsed, cursor=cursor)


def _ticket_filters(
    status: str | None, project_id: str | None, needs_triage: str | None
) -> TicketFilters:
    code: Literal["INVALID_FILTER"] = "INVALID_FILTER"
    if any(
        value is not None and len(value) > MAX_FILTER_LENGTH
        for value in (status, project_id, needs_triage)
    ):
        raise QueryInputError(code)
    if needs_triage is None:
        triage = None
    else:
        values = {"true": True, "false": False}
        if needs_triage not in values:
            raise QueryInputError(code)
        triage = values[needs_triage]
    return TicketFilters(status=status, project_id=project_id, needs_triage=triage)


def _error_response(code: str, status_code: int) -> JSONResponse:
    response = JSONResponse(ErrorResponse(code=code).model_dump(), status_code=status_code)
    apply_security_headers(response.headers)
    return response
