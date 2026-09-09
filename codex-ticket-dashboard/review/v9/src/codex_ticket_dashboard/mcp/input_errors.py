"""Closed repair hints for known public tool input validation failures."""

from dataclasses import dataclass
from typing import Final

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from codex_ticket_dashboard.mcp.schemas import SchemaContractError


@dataclass(frozen=True, slots=True)
class _ToolInput:
    model: str
    fields: tuple[str, ...]
    contracts: tuple[str, ...] = ()


_TOOLS: Final[dict[str, _ToolInput]] = {
    "ticket_preflight_record": _ToolInput(
        "TicketPreflightRequest",
        (
            "context",
            "disposition",
            "ticket_id",
            "classification",
            "goal",
            "non_goals",
            "acceptance_criteria",
            "declared_git_requirement",
            "declared_wiki_requirement",
        ),
        ("PREFLIGHT_TICKET_SHAPE", "PREFLIGHT_CLASSIFICATION_MISMATCH"),
    ),
    "task_upsert": _ToolInput(
        "TaskUpsertRequest",
        (
            "context",
            "ticket_id",
            "work_item_id",
            "parent_work_item_id",
            "kind",
            "title",
            "status",
            "acceptance_criteria",
            "user_decision_event_id",
        ),
        (
            "WORK_ITEM_PARENT_MISMATCH",
            "WORK_ITEM_DECISION_MISMATCH",
            "WORK_ITEM_REMOVAL_TARGET_REQUIRED",
            "WORK_ITEM_DECISION_DEPENDENCY_REQUIRED",
        ),
    ),
    "ticket_status_update": _ToolInput(
        "TicketStatusUpdateRequest",
        (
            "context",
            "ticket_id",
            "from_status",
            "to_status",
            "authority",
            "user_decision_event_id",
            "transition_turn_id",
            "summary_event_id",
            "required_gate_event_ids",
            "affected_work_item_ids",
            "affected_work_item_result_event_ids",
            "reason",
            "evidence_refs",
        ),
        (
            "TRANSITION_TURN_MISMATCH",
            "STATUS_AUTHORITY_SHAPE",
            "STATUS_DECISION_MISMATCH",
            "STATUS_DECISION_DEPENDENCY_REQUIRED",
            "IN_REVIEW_FACTS_REQUIRED",
            "IN_REVIEW_DEPENDENCY_REQUIRED",
            "DUPLICATE_REVIEW_CLAIM",
        ),
    ),
    "ticket_user_decision_record": _ToolInput(
        "TicketUserDecisionRequest",
        (
            "context",
            "ticket_id",
            "source_turn_id",
            "decision",
            "decision_summary",
            "content_type",
            "content_length",
            "content_digest",
        ),
    ),
    "ticket_turn_summary": _ToolInput(
        "TicketTurnSummaryRequest",
        (
            "context",
            "ticket_id",
            "request_feedback_summary",
            "change_surface",
            "verification",
            "outcome",
            "blockers",
            "user_decisions",
            "next_step",
            "affected_work_item_ids",
            "proposed_status",
        ),
    ),
    "git_gate_report": _ToolInput(
        "GitGateReportRequest",
        (
            "context",
            "ticket_id",
            "declared_requirement",
            "resolved_requirement",
            "authority_source",
            "authority_ceiling",
            "policy_snapshot_id",
            "result",
            "repo_key",
            "branch",
            "head_before",
            "head_after",
            "commit_sha",
            "push_state",
            "changed_paths",
            "reason",
        ),
        ("GIT_REPOSITORY_MISMATCH",),
    ),
    "wiki_update_record": _ToolInput(
        "WikiUpdateRecordRequest",
        (
            "context",
            "ticket_id",
            "declared_requirement",
            "resolved_requirement",
            "result",
            "wiki_root_kind",
            "policy_snapshot_id",
            "relative_paths",
            "section_markers",
            "sha256_before",
            "sha256_after",
            "required_fields_present",
            "strict_utf8_ok",
            "reason",
        ),
        ("WIKI_PATH_INVALID", "WIKI_DIGEST_SET_MISMATCH"),
    ),
}
_ERROR_TYPES: Final[dict[str, str]] = {
    "missing": "MISSING_FIELD",
    "extra_forbidden": "UNKNOWN_FIELD",
    "enum": "INVALID_ENUM",
    "literal_error": "INVALID_ENUM",
    "string_pattern_mismatch": "INVALID_FORMAT",
    "string_too_short": "SIZE_LIMIT",
    "string_too_long": "SIZE_LIMIT",
    "too_short": "SIZE_LIMIT",
    "too_long": "SIZE_LIMIT",
    "greater_than_equal": "SIZE_LIMIT",
    "less_than_equal": "SIZE_LIMIT",
    "string_type": "INVALID_TYPE",
    "bool_type": "INVALID_TYPE",
    "bool_parsing": "INVALID_TYPE",
    "int_type": "INVALID_TYPE",
    "int_parsing": "INVALID_TYPE",
    "dict_type": "INVALID_TYPE",
    "tuple_type": "INVALID_TYPE",
    "model_type": "INVALID_TYPE",
    "model_attributes_type": "INVALID_TYPE",
    "path_type": "INVALID_TYPE",
}
_CONTRACT_HINTS: Final[dict[str, str]] = {
    "WIKI_PATH_INVALID": "RELATIVE_POSIX_PATH_REQUIRED",
    "WIKI_DIGEST_SET_MISMATCH": "PATH_DIGEST_KEYS_MUST_MATCH",
}


def input_error_message(tool: str, error: ValidationError) -> str:
    """Expose at most three static hints; never serialize submitted error details."""
    rule = _TOOLS.get(tool)
    if rule is None or error.title not in {rule.model, f"{tool}Arguments"}:
        return "INVALID_TOOL_INPUT"
    hints = sorted(
        {
            _hint(rule, detail, sdk_model=error.title != rule.model)
            for detail in error.errors(include_url=False, include_input=False)
        }
    )[:3]
    if not hints:
        return "INVALID_TOOL_INPUT"
    return f"INVALID_TOOL_INPUT: tool={tool} hints={','.join(hints)}"


def _hint(rule: _ToolInput, detail: ErrorDetails, *, sdk_model: bool) -> str:
    location = detail["loc"]
    if sdk_model:
        location = location[1:] if location and location[0] == "request" else ()
    field = next((name for name in rule.fields if location and location[0] == name), "request")
    code = _ERROR_TYPES.get(detail["type"], "INVALID_VALUE")
    if detail["type"] == "string_pattern_mismatch" and field in {"sha256_before", "sha256_after"}:
        code = "HASH_LOWERCASE_HEX64_REQUIRED"
    match detail:
        case {"type": "value_error", "ctx": {"error": SchemaContractError() as cause}}:
            if type(cause) is SchemaContractError:
                allowed = (*rule.contracts, "DUPLICATE_DEPENDENCY")
                contract = next((name for name in allowed if name == cause.code), None)
                if contract is not None:
                    return f"{field}/{_CONTRACT_HINTS.get(contract, contract)}"
        case _:
            return f"{field}/{code}"
    return f"{field}/{code}"
