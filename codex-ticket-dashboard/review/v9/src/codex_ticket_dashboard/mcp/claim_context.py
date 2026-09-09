"""Validate explicit Stop causation without treating a budget marker as acceptance."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Never

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import JsonValue, TypeAdapter

from codex_ticket_dashboard.domain.events import EventEnvelope, ValidatedEventId
from codex_ticket_dashboard.ingest.recovery import read_safe_event, scan_spool
from codex_ticket_dashboard.lifecycle.continuation import read_claim
from codex_ticket_dashboard.lifecycle.contracts import LifecyclePayload
from codex_ticket_dashboard.lifecycle.receipts import accepted_copy_exists
from codex_ticket_dashboard.storage.causation_queries import (
    ClaimSource,
    OriginalIdentity,
    applied_claim,
    bound_claim_id,
    original_identity,
)
from codex_ticket_dashboard.storage.path_security import DataRootPaths
from codex_ticket_dashboard.storage.readonly_observation import read_observation_database

_EVENT_ID: Final[TypeAdapter[str]] = TypeAdapter(ValidatedEventId)
_DEPENDENCIES: Final[TypeAdapter[tuple[str, ...]]] = TypeAdapter(tuple[ValidatedEventId, ...])


@dataclass(frozen=True, slots=True)
class CorrectionLookup:
    """Official current tuple plus optional explicit cause, never a guessed original turn."""

    thread_id: str
    turn_id: str | None
    parent_thread_id: str | None
    cause_event_id: str | None


@dataclass(frozen=True, slots=True)
class CorrectionContext:
    """A unique original ticket and source authorized by accepted protected Stop evidence."""

    source: ClaimSource
    original: OriginalIdentity


def resolve_correction_context(
    paths: DataRootPaths, lookup: CorrectionLookup
) -> CorrectionContext | None:
    """Read exact accepted/applied cause and bind at most one official continuation turn."""
    if lookup.turn_id is None:
        _reject()
    database = paths.data / "dashboard.sqlite3"
    if not database.exists():
        return None
    source: ClaimSource | None = None
    with read_observation_database(database, paths.root) as connection:
        event_id = lookup.cause_event_id or bound_claim_id(
            connection,
            lookup.thread_id,
            lookup.turn_id,
        )
        if event_id is not None:
            source = applied_claim(connection, event_id)
    if event_id is None:
        return None
    if source is None:
        source = _accepted_source(paths, event_id)
    if source is None:
        return None
    if (
        source.thread_id != lookup.thread_id
        or source.project_id is None
        or source.state in {"NOT_CONTINUED", "UNVERIFIED"}
        or source.continuation_turn_id not in {None, lookup.turn_id}
    ):
        _reject()
    budget = read_claim(paths, source.claim_key)
    if budget is None or (
        budget.claim_event_id,
        budget.source_host,
        budget.thread_id,
        budget.original_turn_id,
    ) != (source.event_id, source.source_host, source.thread_id, source.original_turn_id):
        _reject()
    with read_observation_database(database, paths.root) as connection:
        original = original_identity(connection, source)
    if original is None or original.parent_thread_id != lookup.parent_thread_id:
        _reject()
    return CorrectionContext(source, original)


def _accepted_source(paths: DataRootPaths, event_id: str) -> ClaimSource | None:
    matches = [path for path in scan_spool(paths) if path.name.endswith(f"__{event_id}.json")]
    if len(matches) != 1:
        return None
    collected = read_safe_event(matches[0])
    if collected is None or collected.event_type.value != "TURN_STOPPED":
        return None
    event = EventEnvelope[LifecyclePayload].model_validate(collected.model_dump())
    stop = event.payload.stop_claim
    if stop is None or not accepted_copy_exists(paths, event):
        return None
    return ClaimSource(
        event_id=event.event_id,
        claim_key=stop.claim_key,
        source_host=event.payload.source_host,
        thread_id=event.payload.thread_id,
        original_turn_id=stop.original_turn_id,
        continuation_turn_id=stop.continuation_turn_id,
        state=stop.state,
        project_observation_id=event.project_observation_id,
        project_id=event.project_id,
        repo_key=event.repo_key,
        parent_thread_id=event.payload.parent_thread_id,
    )


def cause_event_id(request: Mapping[str, JsonValue]) -> str | None:
    """Validate an existing context cause before using it in an exact file lookup."""
    context = request.get("context")
    if context is None:
        return None
    if not isinstance(context, dict):
        _reject()
    cause = context.get("causation_event_id")
    return _EVENT_ID.validate_python(cause) if cause is not None else None


def correction_request(
    request: Mapping[str, JsonValue],
    correction: CorrectionContext,
    tool_name: str | None,
) -> dict[str, JsonValue]:
    """Keep correction work on the one witnessed ticket and add its applied-source dependency."""
    if request.get("ticket_id", correction.original.ticket_id) != correction.original.ticket_id:
        _reject()
    if tool_name == "ticket_preflight_record" and request.get("disposition") != "LINK_EXISTING":
        _reject()
    context = request.get("context", {})
    if not isinstance(context, dict):
        _reject()
    dependencies = _DEPENDENCIES.validate_python(context.get("depends_on_event_ids", []))
    cause = correction.source.event_id
    return {
        **request,
        "ticket_id": correction.original.ticket_id,
        "context": {
            **context,
            "causation_event_id": cause,
            "depends_on_event_ids": list(dict.fromkeys((*dependencies, cause))),
        },
    }


def _reject() -> Never:
    message = "CORRECTION_CAUSE_CONFLICT"
    raise ToolError(message)
