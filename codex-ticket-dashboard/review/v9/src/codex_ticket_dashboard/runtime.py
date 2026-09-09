"""Explicit local dashboard runtime with one filesystem-notification watcher."""

import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path
from typing import Annotated, ClassVar, Literal

import anyio
import typer
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field
from watchfiles import awatch

from codex_ticket_dashboard.compliance.runtime_authority import verify_runtime_authority
from codex_ticket_dashboard.compliance.runtime_authority_models import RuntimeAuthorityError
from codex_ticket_dashboard.config import load_dashboard_config
from codex_ticket_dashboard.ingest.collector import Collector
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.models import DatabaseConfig
from codex_ticket_dashboard.storage.path_security import (
    initialize_data_root,
    secure_owner_only_file,
)
from codex_ticket_dashboard.storage.runtime_execution import verify_protected_execution
from codex_ticket_dashboard.web.dashboard import create_dashboard_app


class RuntimeProcessState(BaseModel):
    """Bind one live listener to its exact config, state path, and Python runtime."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    pid: Annotated[int, Field(gt=0)]
    launcher_pid: Annotated[int, Field(gt=0)]
    port: Annotated[int, Field(ge=1025, le=65535)]
    config_path_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    state_path_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    venv_executable: str


def _path_digest(path: Path) -> str:
    return sha256(str(path).encode()).hexdigest()


async def watch_incoming(collector: Collector, incoming: Path) -> None:
    """Rescan once for each delivered native filesystem notification batch."""
    async for _changes in awatch(incoming, recursive=False, force_polling=False):
        _ = collector.notification_hint()


def create_runtime(
    config_path: Path,
    *,
    port: int,
    task_authority: Path | None = None,
    task_authority_sha256: str | None = None,
) -> FastAPI:
    """Create the local-only application from an explicit approved configuration."""
    config = load_dashboard_config(config_path)
    authority = None
    if (task_authority is None) != (task_authority_sha256 is None):
        raise RuntimeAuthorityError(code="TASK_AUTHORITY_PAIR_REQUIRED")
    if task_authority is not None and task_authority_sha256 is not None:
        authority = verify_runtime_authority(
            config, config_path, task_authority, task_authority_sha256
        )
    paths = initialize_data_root(config.data_root)
    database = Database(DatabaseConfig(paths.data / "dashboard.sqlite3"))
    database.migrate()
    collector = Collector(database, paths)
    if authority is not None:
        collector.bootstrap_runtime(authority)

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncGenerator[None, None]:
        async with anyio.create_task_group() as task_group:
            _ = task_group.start_soon(watch_incoming, collector, paths.incoming)
            await anyio.lowlevel.checkpoint()
            _ = collector.startup_scan()
            try:
                yield
            finally:
                task_group.cancel_scope.cancel()

    app = create_dashboard_app(database, port=port)
    app.router.lifespan_context = lifespan
    return app


def _runtime_executable(
    *,
    config_path: Path | None = None,
    task_authority: Path | None = None,
    task_authority_sha256: str | None = None,
    execution_approval: Path | None = None,
    execution_approval_sha256: str | None = None,
) -> Path:
    if execution_approval is not None or execution_approval_sha256 is not None:
        if (
            execution_approval is None
            or execution_approval_sha256 is None
            or config_path is None
            or task_authority is None
            or task_authority_sha256 is None
        ):
            raise RuntimeAuthorityError(code="EXECUTION_APPROVAL_PAIR_REQUIRED")
        return verify_protected_execution(
            execution_approval,
            execution_approval_sha256,
            config_path=config_path,
            task_authority_path=task_authority,
            task_authority_sha256=task_authority_sha256,
            running_executable=Path(sys.executable).resolve(strict=True),
            runtime_module=Path(__file__).resolve(strict=True),
            import_paths=tuple(Path(path).resolve(strict=True) for path in sys.path),
            bytecode_disabled=sys.dont_write_bytecode,
            isolation_verified=(
                sys.flags.isolated == 1
                and sys.flags.ignore_environment == 1
                and sys.flags.no_user_site == 1
                and sys.flags.no_site == 1
                and sys.flags.safe_path
            ),
        )
    project_root = Path(__file__).resolve().parents[2]
    venv_executable = (project_root / ".venv" / "Scripts" / "python.exe").resolve(strict=True)
    running_executable = Path(sys.executable).resolve(strict=True)
    if not running_executable.samefile(venv_executable):
        message = "PROJECT_VENV_REQUIRED"
        raise RuntimeError(message)
    return venv_executable


def _write_process_state(
    config_path: Path,
    state_path: Path,
    port: int,
    approved_executable: Path | None = None,
) -> RuntimeProcessState:
    venv_executable = approved_executable or _runtime_executable()
    state = RuntimeProcessState(
        pid=os.getpid(),
        launcher_pid=os.getppid(),
        port=port,
        config_path_sha256=_path_digest(config_path),
        state_path_sha256=_path_digest(state_path),
        venv_executable=str(venv_executable),
    )
    temporary = state_path.with_name(f"{state_path.name}.{state.pid}.tmp")
    try:
        _ = secure_owner_only_file(temporary, state_path.parent, create=True)
        with temporary.open("w", encoding="utf-8", newline="\n") as output:
            _ = output.write(state.model_dump_json())
            output.flush()
            os.fsync(output.fileno())
        _ = temporary.rename(state_path)
        _ = secure_owner_only_file(state_path, state_path.parent, create=False)
    finally:
        temporary.unlink(missing_ok=True)
    return state


def _remove_owned_state(state_path: Path, pid: int) -> None:
    try:
        state = RuntimeProcessState.model_validate_json(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if state.pid == pid:
        state_path.unlink(missing_ok=True)


def run(  # noqa: PLR0913 -- explicit independent externally pinned approvals.
    config_path: Path,
    state_path: Path,
    *,
    port: int,
    task_authority: Path | None = None,
    task_authority_sha256: str | None = None,
    execution_approval: Path | None = None,
    execution_approval_sha256: str | None = None,
) -> None:
    """Run one loopback-only Uvicorn process for an explicit port."""
    canonical_config = config_path.resolve(strict=True)
    canonical_state = state_path.resolve(strict=False)
    executable = _runtime_executable(
        config_path=canonical_config,
        task_authority=task_authority,
        task_authority_sha256=task_authority_sha256,
        execution_approval=execution_approval,
        execution_approval_sha256=execution_approval_sha256,
    )
    app = create_runtime(
        canonical_config,
        port=port,
        task_authority=task_authority,
        task_authority_sha256=task_authority_sha256,
    )
    state = _write_process_state(canonical_config, canonical_state, port, executable)
    try:
        uvicorn.run(app, host="127.0.0.1", port=port, access_log=False)
    finally:
        _remove_owned_state(canonical_state, state.pid)


def main(  # noqa: PLR0913, PLR0917 -- Typer exposes explicit independent approval options.
    config: Annotated[Path, typer.Option("--config")],
    port: Annotated[int, typer.Option("--port", min=1025, max=65535)],
    state: Annotated[Path, typer.Option("--state")],
    task_authority: Annotated[Path | None, typer.Option("--task-authority")] = None,
    task_authority_sha256: Annotated[str | None, typer.Option("--task-authority-sha256")] = None,
    execution_approval: Annotated[Path | None, typer.Option("--execution-approval")] = None,
    execution_approval_sha256: Annotated[
        str | None, typer.Option("--execution-approval-sha256")
    ] = None,
) -> None:
    """Start the dashboard through an explicit, safely tokenized module entrypoint."""
    try:
        run(
            config,
            state,
            port=port,
            task_authority=task_authority,
            task_authority_sha256=task_authority_sha256,
            execution_approval=execution_approval,
            execution_approval_sha256=execution_approval_sha256,
        )
    except RuntimeAuthorityError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(1) from None


if __name__ == "__main__":
    typer.run(main)
