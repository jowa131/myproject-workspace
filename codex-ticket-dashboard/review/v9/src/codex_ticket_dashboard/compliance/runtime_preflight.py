"""Read-only existing-database compatibility preflight for an approved runtime."""

import argparse
import sys
from pathlib import Path
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from codex_ticket_dashboard.compliance.runtime_authority import verify_runtime_authority
from codex_ticket_dashboard.compliance.runtime_authority_models import RuntimeAuthorityError
from codex_ticket_dashboard.config import ConfigLoadError, load_dashboard_config
from codex_ticket_dashboard.domain.events import ValidatedProjectId
from codex_ticket_dashboard.ingest.runtime_bootstrap_state import (
    RuntimeBootstrapAction,
    RuntimeBootstrapDecision,
    evaluate_runtime_bootstrap_state,
)
from codex_ticket_dashboard.storage.readonly_observation import (
    ReadOnlyObservationError,
    read_observation_database,
)

PreflightCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")]


class RuntimePreflightResult(BaseModel):
    """Machine-readable decision with no paths, source content, or database values."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal[1] = 1
    status: Literal["READY", "BLOCKED"]
    code: PreflightCode
    action: RuntimeBootstrapAction | None
    project_id: ValidatedProjectId | None


def preflight_runtime(
    config_path: Path,
    task_authority_path: Path,
    task_authority_sha256: str,
) -> RuntimePreflightResult:
    """Verify current pins and run startup's compatibility decision without storage mutation."""
    decision: RuntimeBootstrapDecision | None = None
    bootstrap_error: RuntimeAuthorityError | None = None
    try:
        config = load_dashboard_config(config_path)
        authority = verify_runtime_authority(
            config,
            config_path,
            task_authority_path,
            task_authority_sha256,
        )
        database_path = config.data_root / "data/dashboard.sqlite3"
        with read_observation_database(database_path, config.data_root) as connection:
            try:
                decision = evaluate_runtime_bootstrap_state(connection, authority)
            except RuntimeAuthorityError as error:
                bootstrap_error = error
    except ConfigLoadError as error:
        return _blocked(error.code)
    except RuntimeAuthorityError as error:
        return _blocked(error.code)
    except ReadOnlyObservationError as error:
        return _blocked(error.code)
    if bootstrap_error is not None:
        return _blocked(bootstrap_error.code)
    if decision is None:
        return _blocked("BOOTSTRAP_STATE_INCOMPLETE")
    return RuntimePreflightResult(
        status="READY",
        code="RUNTIME_BOOTSTRAP_READY",
        action=decision.action,
        project_id=authority.declaration.project_id,
    )


def _blocked(code: str) -> RuntimePreflightResult:
    return RuntimePreflightResult(
        status="BLOCKED",
        code=code,
        action=None,
        project_id=None,
    )


class _Arguments(argparse.Namespace):
    def __init__(self) -> None:
        super().__init__()
        self.config: Path = Path()
        self.task_authority: Path = Path()
        self.task_authority_sha256: str = ""


def cli() -> None:
    """Emit one redacted JSON result and use exit one for a blocked preflight."""
    parser = argparse.ArgumentParser()
    _ = parser.add_argument("--config", required=True, type=Path)
    _ = parser.add_argument("--task-authority", required=True, type=Path)
    _ = parser.add_argument("--task-authority-sha256", required=True)
    arguments = _Arguments()
    _ = parser.parse_args(namespace=arguments)
    result = preflight_runtime(
        arguments.config,
        arguments.task_authority,
        arguments.task_authority_sha256,
    )
    _ = sys.stdout.write(result.model_dump_json() + "\n")
    if result.status == "BLOCKED":
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
