from __future__ import annotations

from typing import TYPE_CHECKING

import anyio
import pytest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import JsonValue, TypeAdapter

from codex_ticket_dashboard.mcp.official_context import ContextResolver, parse_official_metadata
from codex_ticket_dashboard.mcp.policy_context import GENERATED_FIELDS
from codex_ticket_dashboard.mcp.server import create_server
from codex_ticket_dashboard.storage.spool import SpoolWriter
from tests.integration.stop_fixture import stop_fixture

if TYPE_CHECKING:
    from pathlib import Path

    from mcp.server.mcpserver import MCPServer

_MAP = TypeAdapter(dict[str, JsonValue])


async def _schema_properties(
    server: MCPServer[None], tool_name: str, schema_name: str
) -> set[str]:
    tools = await server.list_tools()
    tool = next(item for item in tools if item.name == tool_name)
    schema = _MAP.validate_python(tool.input_schema)
    definitions = _MAP.validate_python(schema["$defs"])
    definition = _MAP.validate_python(definitions[schema_name])
    properties = _MAP.validate_python(definition["properties"])
    return set(properties)


def test_product_schema_hides_server_fields_and_keeps_caller_fields(tmp_path: Path) -> None:
    # Given
    fixture = stop_fixture(tmp_path)
    server = create_server(SpoolWriter(fixture.paths), fixture.paths)

    # When
    git_fields = anyio.run(
        _schema_properties, server, "git_gate_report", "GitGateReportRequest"
    )
    status_fields = anyio.run(
        _schema_properties, server, "ticket_status_update", "TicketStatusUpdateRequest"
    )

    # Then
    assert not ({"context"} | GENERATED_FIELDS["GitGateReportRequest"]) & git_fields
    assert {"declared_requirement", "result", "branch", "changed_paths"} <= git_fields
    assert {"context", "transition_turn_id"}.isdisjoint(status_fields)
    assert {"from_status", "to_status", "authority", "reason"} <= status_fields


def test_resolverless_schema_preserves_direct_request_fields(tmp_path: Path) -> None:
    # Given
    fixture = stop_fixture(tmp_path)
    server = create_server(SpoolWriter(fixture.paths))

    # When
    fields = anyio.run(_schema_properties, server, "git_gate_report", "GitGateReportRequest")

    # Then
    assert {"context"} | GENERATED_FIELDS["GitGateReportRequest"] <= fields


def test_resolver_binds_omitted_fields_and_rejects_explicit_conflict(tmp_path: Path) -> None:
    # Given
    fixture = stop_fixture(tmp_path)
    metadata = parse_official_metadata(
        {
            "threadId": "synthetic",
            "x-codex-turn-metadata": {"thread_id": "synthetic", "turn_id": "original"},
        }
    )
    assert metadata is not None
    request: dict[str, JsonValue] = {
        "ticket_id": fixture.ticket_id,
        "declared_requirement": "NOT_APPLICABLE",
        "result": "N/A",
        "branch": "synthetic",
        "push_state": "N/A",
        "changed_paths": [],
    }
    resolver = ContextResolver(fixture.paths)

    # When
    bound = resolver.bind(request, metadata, "git_gate_report").request

    # Then
    assert bound["context"] is not None
    assert bound["resolved_requirement"] == "NOT_APPLICABLE"
    assert bound["declared_requirement"] == "NOT_APPLICABLE"
    assert bound["result"] == "N/A"
    with pytest.raises(ToolError, match="MODEL_POLICY_CONTEXT_CONFLICT"):
        _ = resolver.bind(
            {**request, "authority_source": "caller-owned"},
            metadata,
            "git_gate_report",
        )
