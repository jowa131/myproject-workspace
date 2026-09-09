"""Local nonblocking lifecycle Hook entrypoint with redacted failure output."""

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from pydantic import TypeAdapter, ValidationError

from codex_ticket_dashboard.compliance.project_registry import ProjectResolution
from codex_ticket_dashboard.config import ConfigLoadError, load_dashboard_config
from codex_ticket_dashboard.domain.events import ProjectResolutionState
from codex_ticket_dashboard.lifecycle.admission import admit_observation, observation_envelope
from codex_ticket_dashboard.lifecycle.command_diagnostics import (
    ProcessingStage,
    ResultCode,
    parse_diagnostic_context,
    publish_command_diagnostic,
)
from codex_ticket_dashboard.lifecycle.identity import resolve_identity
from codex_ticket_dashboard.lifecycle.normalization import (
    MAX_INPUT_BYTES,
    NormalizedHook,
    ObservationError,
    SourceKind,
    normalize_hook,
)
from codex_ticket_dashboard.lifecycle.stop_observer import observe_stop
from codex_ticket_dashboard.recording_guidance import RECORDING_GUIDANCE
from codex_ticket_dashboard.storage.path_security import DataRootPaths, data_root_paths


def _observe(
    paths: DataRootPaths,
    hook: NormalizedHook,
    identity: ProjectResolution,
) -> str | None:
    if hook.payload.hook_event == "Stop":
        return observe_stop(paths, hook, identity)
    event = observation_envelope(hook.payload, identity)
    _ = admit_observation(paths, event)
    if (
        hook.payload.hook_event == "UserPromptSubmit"
        and identity.state is ProjectResolutionState.RESOLVED
    ):
        return json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": RECORDING_GUIDANCE,
                }
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    return None


def observe(raw: bytes, config: Path, source_host: str, source_kind: SourceKind) -> str | None:
    """Record one Hook observation without requiring MCP availability or changing SQLite."""
    settings = load_dashboard_config(config)
    hook = normalize_hook(raw, source_host, source_kind)
    identity = resolve_identity(settings, hook)
    return _observe(data_root_paths(settings.data_root), hook, identity)


def main(
    config: Annotated[Path, typer.Option("--config")],
    source_host: Annotated[str, typer.Option("--source-host")],
    source_kind: Annotated[str, typer.Option("--source-kind")] = "unknown",
) -> None:
    """Emit fixed admitted input guidance; expected failures never block the parent turn."""
    code: ResultCode = "OBSERVER_INTERNAL_ERROR"
    paths: DataRootPaths | None = None
    stage: ProcessingStage = "NORMALIZATION"
    context = parse_diagnostic_context(b"")
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        context = parse_diagnostic_context(raw)
        settings = load_dashboard_config(config)
        paths = data_root_paths(settings.data_root)
        publish_command_diagnostic(paths, context, ("STARTED", stage, "PENDING"))
        adapter: TypeAdapter[SourceKind] = TypeAdapter(SourceKind)
        kind = adapter.validate_python(source_kind)
        hook = normalize_hook(raw, source_host, kind)
        stage = "IDENTITY"
        identity = resolve_identity(settings, hook)
        stage = "ADMISSION"
        response = _observe(paths, hook, identity)
        if response is not None:
            typer.echo(response)
    except ObservationError as error:
        code = error.code
    except ConfigLoadError:
        code = "CONFIG_INVALID"
    except ValidationError:
        code = "ADMISSION_UNVERIFIED"
    except (UnicodeError, ValueError):
        code = "INPUT_INVALID"
    except OSError:
        code = "STORAGE_UNAVAILABLE"
    except Exception:  # noqa: BLE001 -- Hook boundary must never expose raw exception locals.
        code = "OBSERVER_INTERNAL_ERROR"
    else:
        publish_command_diagnostic(paths, context, ("SUCCEEDED", stage, "RECORDED"))
        return
    if paths is not None:
        publish_command_diagnostic(paths, context, ("FAILED", stage, code))
    typer.echo(json.dumps({"code": code, "recording": "UNVERIFIED"}), err=True)
    raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(main)
