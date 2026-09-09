"""Public outer ASGI dashboard with a separately mounted API application."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import RequestResponseEndpoint

from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.web.app import create_app
from codex_ticket_dashboard.web.pages import PageRenderer
from codex_ticket_dashboard.web.queries import QueryRepository
from codex_ticket_dashboard.web.security import (
    SecurityConfig,
    apply_security_headers,
    request_rejection_code,
)


def create_dashboard_app(database: Database, *, port: int) -> FastAPI:
    """Create the secured HTML shell and mount the unmodified API last."""
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    _install_boundary(app, SecurityConfig(port=port))
    pages = PageRenderer(QueryRepository(database))
    _install_pages(app, pages)
    static_path = Path(__file__).with_name("static")
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    app.mount("/", create_app(database, port=port))
    return app


def _install_boundary(app: FastAPI, security: SecurityConfig) -> None:
    async def local_boundary(request: Request, call_next: RequestResponseEndpoint) -> Response:
        rejection = request_rejection_code(request, security)
        if rejection is None:
            response = await call_next(request)
        else:
            response = HTMLResponse(f"<h1>{rejection}</h1>", status_code=400)
        apply_security_headers(response.headers)
        return response

    _ = app.middleware("http")(local_boundary)


def _install_pages(app: FastAPI, pages: PageRenderer) -> None:
    async def projects(request: Request) -> HTMLResponse:
        return pages.response(request, "projects")

    async def board(request: Request) -> HTMLResponse:
        return pages.response(request, "board")

    async def compliance(request: Request) -> HTMLResponse:
        return pages.response(request, "compliance")

    async def issues(request: Request) -> HTMLResponse:
        return pages.response(request, "issues")

    app.add_api_route("/", projects, methods=["GET", "HEAD"], response_class=HTMLResponse)
    app.add_api_route("/board", board, methods=["GET", "HEAD"], response_class=HTMLResponse)
    app.add_api_route(
        "/activities", pages.activities, methods=["GET", "HEAD"], response_class=HTMLResponse
    )
    app.add_api_route(
        "/tickets/{ticket_id}", pages.ticket, methods=["GET", "HEAD"], response_class=HTMLResponse
    )
    app.add_api_route(
        "/compliance", compliance, methods=["GET", "HEAD"], response_class=HTMLResponse
    )
    app.add_api_route(
        "/ingest/issues", issues, methods=["GET", "HEAD"], response_class=HTMLResponse
    )
