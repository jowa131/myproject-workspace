"""Bind official MCP request metadata to accepted structured observer context."""

from collections.abc import Mapping
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Final

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, ValidationError

from codex_ticket_dashboard.config import DashboardConfig
from codex_ticket_dashboard.domain.source_metadata import McpContextWitness
from codex_ticket_dashboard.ingest.dead_letter import parse_collected_event
from codex_ticket_dashboard.ingest.recovery import scan_spool
from codex_ticket_dashboard.lifecycle.contracts import (
    LifecyclePayload,
    MetadataId,
    logical_thread_id,
)
from codex_ticket_dashboard.mcp.claim_context import (
    CorrectionLookup,
    cause_event_id,
    correction_request,
    resolve_correction_context,
)
from codex_ticket_dashboard.mcp.policy_context import (
    ObserverContext,
    bind_policy_fields,
)
from codex_ticket_dashboard.mcp.schemas import EventContext
from codex_ticket_dashboard.storage.path_security import DataRootPaths
from codex_ticket_dashboard.storage.readonly_observation import read_observation_database


class TurnMetadata(BaseModel):
    """Exact current Codex metadata names, retaining no other request material."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore", strict=True)
    thread_id: MetadataId | None = None
    turn_id: MetadataId | None = None
    parent_thread_id: MetadataId | None = None


class OfficialMetadata(BaseModel):
    """Official metadata presence is separate from legacy explicit context."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore", strict=True)
    thread_id: MetadataId = Field(alias="threadId")
    turn: TurnMetadata = Field(alias="x-codex-turn-metadata")


def parse_official_metadata(raw: Mapping[str, JsonValue] | None) -> OfficialMetadata | None:
    """Reject partial/conflicting official tuples without silently using legacy IDs."""
    if raw is None or not ({"threadId", "x-codex-turn-metadata"} & raw.keys()):
        return None
    try:
        metadata = OfficialMetadata.model_validate(raw)
    except ValidationError:
        msg = "OFFICIAL_CONTEXT_INVALID"
        raise ToolError(msg) from None
    if metadata.turn.thread_id not in {None, metadata.thread_id}:
        msg = "OFFICIAL_CONTEXT_CONFLICT"
        raise ToolError(msg)
    if metadata.turn.turn_id is None:
        msg = "OFFICIAL_TURN_MISSING"
        raise ToolError(msg)
    if metadata.turn.parent_thread_id == metadata.thread_id:
        msg = "OFFICIAL_CONTEXT_CONFLICT"
        raise ToolError(msg)
    return metadata


_JSON: Final[TypeAdapter[JsonValue]] = TypeAdapter(JsonValue)
_MAP: Final = TypeAdapter(dict[str, JsonValue])
_ROWS: Final = TypeAdapter(
    list[tuple[str, str, str | None, str | None, str, str, str | None, str | None]]
)
CURRENT_WITNESS: Final[ContextVar[McpContextWitness | None]] = ContextVar(
    "mcp_official_witness",
    default=None,
)


@dataclass(frozen=True, slots=True)
class BoundRequest:
    """Server-only witness travels outside the tool's caller-controlled request."""

    request: dict[str, JsonValue]
    witness: McpContextWitness


class ContextResolver:
    """Read accepted spool and database observations; never use unpublished intent."""

    def __init__(self, paths: DataRootPaths, config: DashboardConfig | None = None) -> None:
        """Bind the accepted observation stores and optional authoritative registry."""
        self._paths: DataRootPaths = paths
        self._config: DashboardConfig | None = config

    def bind(  # noqa: C901
        self,
        request: Mapping[str, JsonValue],
        metadata: OfficialMetadata,
        tool_name: str | None = None,
    ) -> BoundRequest:
        """Fill omitted context while rejecting conflicting model identity claims."""
        thread = logical_thread_id(metadata.thread_id)
        turn = metadata.turn.turn_id
        parent = (
            logical_thread_id(metadata.turn.parent_thread_id)
            if metadata.turn.parent_thread_id is not None
            else None
        )
        correction = resolve_correction_context(
            self._paths,
            CorrectionLookup(
                thread,
                turn,
                parent,
                cause_event_id(request),
            ),
        )
        request_data = correction_request(request, correction, tool_name) if correction else request
        candidates = [
            item
            for item in self._observations()
            if item.thread_id == thread and item.turn_id == turn
        ]
        if correction is not None:
            source = correction.source
            candidates.append(
                ObserverContext(
                    source_host=source.source_host,
                    thread_id=thread,
                    turn_id=turn,
                    parent_thread_id=parent,
                    relation_state="VERIFIED",
                    project_observation_id=source.project_observation_id,
                    project_id=source.project_id,
                    repo_key=source.repo_key,
                )
            )
        if not candidates:
            msg = "OBSERVER_CONTEXT_MISSING"
            raise ToolError(msg)
        candidates = [item.with_applied_repository(self._paths) for item in candidates]
        identities = {
            (item.source_host, item.project_observation_id, item.project_id, item.repo_key)
            for item in candidates
        }
        if len(identities) != 1 or any(
            item.relation_state == "CONFLICT"
            or (
                item.parent_thread_id != parent
                and (item.parent_thread_id is not None or item.relation_state == "VERIFIED")
            )
            for item in candidates
        ):
            msg = "OBSERVER_CONTEXT_CONFLICT"
            raise ToolError(msg)
        selected = candidates[0]
        if selected.project_id is None:
            msg = "PROJECT_IDENTITY_UNVERIFIED"
            raise ToolError(msg)
        if self._config is not None and selected.project_id not in {
            project.project_id for project in self._config.projects
        }:
            msg = "PROJECT_REGISTRY_CONFLICT"
            raise ToolError(msg)
        generated: dict[str, JsonValue] = {
            "project_observation_id": selected.project_observation_id,
            "project_id": selected.project_id,
            "repo_key": selected.repo_key,
            "session_id": thread,
            "turn_id": turn,
        }
        supplied = request_data.get("context")
        if supplied is not None:
            try:
                claimed = _MAP.validate_python(supplied)
            except ValidationError:
                msg = "INVALID_TOOL_INPUT"
                raise ToolError(msg) from None
            if any(key in claimed and claimed[key] != value for key, value in generated.items()):
                msg = "MODEL_CONTEXT_CONFLICT"
                raise ToolError(msg)
            generated = {**claimed, **generated}
        try:
            parsed = EventContext.model_validate(generated)
        except ValidationError:
            msg = "INVALID_TOOL_INPUT"
            raise ToolError(msg) from None
        bound: dict[str, JsonValue] = {
            **request_data,
            "context": _JSON.validate_python(parsed.model_dump(mode="json")),
        }
        if tool_name == "ticket_status_update":
            if "transition_turn_id" in request_data and request_data["transition_turn_id"] != turn:
                message = "MODEL_CONTEXT_CONFLICT"
                raise ToolError(message)
            bound["transition_turn_id"] = turn
        bound = bind_policy_fields(
            self._paths, bound, selected.project_id, selected.repo_key, tool_name
        )
        return BoundRequest(
            bound,
            McpContextWitness.model_validate(
                {
                    "source_host": selected.source_host,
                    "thread_id": thread,
                    "turn_id": turn,
                    "parent_thread_id": parent,
                }
            ),
        )

    def _observations(self) -> list[ObserverContext]:
        observations: list[ObserverContext] = []
        path = self._paths.data / "dashboard.sqlite3"
        if path.exists():
            with read_observation_database(path, self._paths.root) as connection:
                rows = _ROWS.validate_python(
                    connection.execute(
                        """SELECT o.source_host,o.thread_id,o.turn_id,
                    COALESCE(o.parent_thread_id,m.parent_thread_id),
                    CASE WHEN m.event_id IS NOT NULL AND o.relation_state!='CONFLICT'
                         THEN 'VERIFIED' ELSE o.relation_state END,o.project_observation_id,
                    COALESCE(o.project_id,r.resolved_project_id),p.repo_key
                    FROM lifecycle_observations o
                    LEFT JOIN event_project_resolutions r
                      ON r.project_observation_id=o.project_observation_id
                    LEFT JOIN projects p ON p.id=COALESCE(o.project_id,r.resolved_project_id)
                    LEFT JOIN lifecycle_mcp_contexts m ON m.source_host=o.source_host
                      AND m.thread_id=o.thread_id AND m.turn_id=o.turn_id""",
                    ).fetchall()
                )
            observations.extend(
                ObserverContext(
                    source_host=row[0],
                    thread_id=row[1],
                    turn_id=row[2],
                    parent_thread_id=row[3],
                    relation_state=row[4],
                    project_observation_id=row[5],
                    project_id=row[6],
                    repo_key=row[7],
                )
                for row in rows
            )
        for event_path in scan_spool(self._paths):
            observation = self._read_event(event_path)
            if observation is not None:
                observations.append(observation)
        return observations

    @staticmethod
    def _read_event(path: Path) -> ObserverContext | None:
        try:
            event = parse_collected_event(_JSON.validate_json(path.read_bytes()))
            payload = LifecyclePayload.model_validate(event.payload.root)
        except (ValidationError, OSError):
            return None
        return ObserverContext(
            source_host=payload.source_host,
            thread_id=payload.thread_id,
            turn_id=payload.turn_id,
            parent_thread_id=payload.parent_thread_id,
            relation_state=payload.relation_state,
            project_observation_id=event.project_observation_id,
            project_id=event.project_id,
            repo_key=event.repo_key,
        )
