"""Canonical fixed recording guidance; never interpolates Hook or conversation content."""

from typing import Final

RECORDING_GUIDANCE: Final = (
    "Automatic structured recording is part of work in this registered project. Before a "
    "normal task, discover codex_ticket_dashboard if needed and call "
    "ticket_preflight_record. Record actual work with task_upsert; before the final reply "
    "record the turn summary and truthful required Git/Wiki gate results. Use returned IDs "
    "and server-bound official context. Never fabricate identity, evidence, gate success, "
    "or user decisions. Respect explicit user restrictions. If recording is unavailable or "
    "context is unverified, continue the requested work and report recording incomplete "
    "once. Never store raw prompts or transcripts. Only a current explicit user decision "
    "may complete, cancel, or reopen a ticket. If preflight rejects a declaration and "
    "supplies verified applied Git/Wiki requirements, correct the declaration from those "
    "values. A summary proposed_status does not change ticket state. After successful "
    "required gate and summary records, request IN_REVIEW through ticket_status_update with"
    " CODEX_RESULT and current returned event/version references. If the evidence does not "
    "support review, use a truthful non-review status and explain the remaining blocker. "
    "For a PLANNED ticket, record its work start with ticket_status_update to IN_PROGRESS "
    "using CODEX_EXECUTION before any CODEX_RESULT transition."
)

_MCP_TOOL_GUIDANCE: Final = (
    "Automatically record current work with these seven tools: preflight first; task_upsert"
    " for tasks; turn summary and applicable Git/Wiki gate records before status review. "
    "Omit context identity: the server binds official current thread/turn metadata to "
    "observer records. Never guess IDs. Retain returned IDs for dependencies. "
    "Missing/conflicting context is unverified. Only explicit user decisions authorize "
    "completion/cancellation/reopen. Store structured summaries only, never raw prompts or "
    "transcripts."
)

MCP_INITIALIZATION_INSTRUCTIONS: Final = RECORDING_GUIDANCE + "\n\n" + _MCP_TOOL_GUIDANCE
