"""Official MCP Python SDK v2 stdio server with seven recording tools."""

from pathlib import Path
from typing import Annotated, assert_never, override

import typer
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import CallToolResult, InputRequiredResult, Tool
from pydantic import JsonValue, TypeAdapter, ValidationError

from codex_ticket_dashboard import mcp as mcp_api
from codex_ticket_dashboard.config import DashboardConfig, load_dashboard_config
from codex_ticket_dashboard.mcp import schemas
from codex_ticket_dashboard.mcp.admission_diagnostics import AdmissionDiagnostics
from codex_ticket_dashboard.mcp.input_errors import input_error_message
from codex_ticket_dashboard.mcp.official_context import (
    CURRENT_WITNESS,
    ContextResolver,
    parse_official_metadata,
)
from codex_ticket_dashboard.mcp.policy_context import GENERATED_FIELDS
from codex_ticket_dashboard.mcp.tools import EventRecorder
from codex_ticket_dashboard.recording_guidance import MCP_INITIALIZATION_INSTRUCTIONS
from codex_ticket_dashboard.storage.path_security import DataRootPaths, initialize_data_root
from codex_ticket_dashboard.storage.spool import SpoolWriter

_INSTRUCTIONS = MCP_INITIALIZATION_INSTRUCTIONS
_MAP = TypeAdapter(dict[str, JsonValue])


class _PrivacySafeMCPServer(MCPServer[None]):
    def __init__(self, resolver: ContextResolver | None, paths: DataRootPaths | None) -> None:
        self._diagnostics: AdmissionDiagnostics = AdmissionDiagnostics(paths)
        super().__init__(
            name="codex-ticket-dashboard",
            version="0.1.0",
            instructions=_INSTRUCTIONS,
            lifespan=self._diagnostics.lifespan,
        )
        self._resolver: ContextResolver | None = resolver

    @override
    async def list_tools(self) -> list[Tool]:
        listed = await super().list_tools()
        for tool in listed:
            schema = _MAP.validate_python(tool.input_schema)
            definitions = schema.get("$defs")
            if isinstance(definitions, dict):
                for schema_name, definition in definitions.items():
                    if isinstance(definition, dict):
                        required = definition.get("required")
                        if isinstance(required, list):
                            optional = {"context"}
                            if schema_name == "TicketStatusUpdateRequest":
                                optional.add("transition_turn_id")
                            optional.update(GENERATED_FIELDS.get(schema_name, ()))
                            definition["required"] = [
                                item for item in required if item not in optional
                            ]
            tool.input_schema = schema
        return listed

    @override
    async def call_tool(
        self,
        name: str,
        arguments: dict[str, JsonValue],
        context: Context[None, JsonValue] | None = None,
    ) -> CallToolResult | InputRequiredResult:
        with self._diagnostics.observe(name):
            witness_token = CURRENT_WITNESS.set(None)
            try:
                metadata = parse_official_metadata(
                    context.request_context.meta if context else None
                )
                bound = arguments
                if metadata is not None:
                    self._diagnostics.mark("official")
                    if self._resolver is None:
                        msg = "OBSERVER_CONTEXT_UNAVAILABLE"
                        raise ToolError(msg)  # noqa: TRY301
                    request = _MAP.validate_python(arguments.get("request"))
                    resolved = self._resolver.bind(request, metadata, name)
                    self._diagnostics.mark("bound")
                    _ = CURRENT_WITNESS.set(resolved.witness)
                    bound = {**arguments, "request": resolved.request}
                result = await super().call_tool(name, bound, context)
                self._diagnostics.returned_flag(
                    result.is_error if isinstance(result, CallToolResult) else None
                )
            except ToolError as error:
                if isinstance(error.__cause__, ValidationError):
                    raise ToolError(input_error_message(name, error.__cause__)) from None
                raise
            except ValidationError as error:
                raise ToolError(input_error_message(name, error)) from None
            finally:
                CURRENT_WITNESS.reset(witness_token)
            return result


def create_server(  # noqa: C901
    writer: SpoolWriter, paths: DataRootPaths | None = None, config: DashboardConfig | None = None
) -> MCPServer[None]:
    """Create the exact event-recording MCP surface over one spool writer."""
    recorder = EventRecorder(writer)
    server = _PrivacySafeMCPServer(ContextResolver(paths, config) if paths else None, paths)

    def record(request: schemas.McpRequest) -> mcp_api.AdmissionReceipt:
        return recorder.record(request, witness=CURRENT_WITNESS.get())

    @server.tool(name="ticket_preflight_record", structured_output=True)
    def ticket_preflight_record(
        request: schemas.TicketPreflightRequest,
    ) -> mcp_api.TicketAdmissionReceipt:
        """Record a typed ticket preflight without executing user work."""
        return _ticket_receipt(record(request))

    @server.tool(name="task_upsert", structured_output=True)
    def task_upsert(
        request: schemas.TaskUpsertRequest,
    ) -> mcp_api.WorkItemAdmissionReceipt:
        """Record one typed task or subtask event."""
        result = record(request)
        match result:
            case mcp_api.WorkItemAdmissionReceipt():
                return result
            case mcp_api.TicketAdmissionReceipt() | mcp_api.UserDecisionAdmissionReceipt():
                raise mcp_api.ReceiptConstructionError
            case unreachable:
                assert_never(unreachable)

    @server.tool(name="ticket_status_update", structured_output=True)
    def ticket_status_update(
        request: schemas.TicketStatusUpdateRequest,
    ) -> mcp_api.TicketAdmissionReceipt:
        """Record a status claim for collector-side authority validation."""
        return _ticket_receipt(record(request))

    @server.tool(name="ticket_user_decision_record", structured_output=True)
    def ticket_user_decision_record(
        request: schemas.TicketUserDecisionRequest,
    ) -> mcp_api.UserDecisionAdmissionReceipt:
        """Record a structure-only explicit-user decision."""
        result = record(request)
        match result:
            case mcp_api.UserDecisionAdmissionReceipt():
                return result
            case mcp_api.TicketAdmissionReceipt() | mcp_api.WorkItemAdmissionReceipt():
                raise mcp_api.ReceiptConstructionError
            case unreachable:
                assert_never(unreachable)

    @server.tool(name="ticket_turn_summary", structured_output=True)
    def ticket_turn_summary(
        request: schemas.TicketTurnSummaryRequest,
    ) -> mcp_api.TicketAdmissionReceipt:
        """Record an allowlisted turn summary with computed metadata."""
        return _ticket_receipt(record(request))

    @server.tool(name="git_gate_report", structured_output=True)
    def git_gate_report(
        request: schemas.GitGateReportRequest,
    ) -> mcp_api.TicketAdmissionReceipt:
        """Record read-only Git gate evidence."""
        return _ticket_receipt(record(request))

    @server.tool(name="wiki_update_record", structured_output=True)
    def wiki_update_record(
        request: schemas.WikiUpdateRecordRequest,
    ) -> mcp_api.TicketAdmissionReceipt:
        """Record read-only Wiki verification evidence without writing Wiki."""
        return _ticket_receipt(record(request))

    _ = (
        ticket_preflight_record,
        task_upsert,
        ticket_status_update,
        ticket_user_decision_record,
        ticket_turn_summary,
        git_gate_report,
        wiki_update_record,
    )
    return server


def _ticket_receipt(result: mcp_api.AdmissionReceipt) -> mcp_api.TicketAdmissionReceipt:
    match result:
        case mcp_api.TicketAdmissionReceipt():
            return result
        case mcp_api.WorkItemAdmissionReceipt() | mcp_api.UserDecisionAdmissionReceipt():
            raise mcp_api.ReceiptConstructionError
        case unreachable:
            assert_never(unreachable)


def main(
    data_root: Annotated[Path, typer.Option("--data-root")],
    config: Annotated[Path | None, typer.Option("--config")] = None,
) -> None:
    """Run the MCP server over stdio using one explicit protected data root."""
    paths = initialize_data_root(data_root)
    loaded = load_dashboard_config(config) if config is not None else None
    if loaded is not None and loaded.data_root.resolve() != paths.root.resolve():
        msg = "CONFIG_DATA_ROOT_CONFLICT"
        raise ToolError(msg)
    create_server(SpoolWriter(paths), paths, loaded).run("stdio")


if __name__ == "__main__":
    typer.run(main)
