"""Seven-tool event construction and atomic spool admission."""

import json
from hashlib import sha256
from typing import assert_never

from codex_ticket_dashboard import mcp as mcp_api
from codex_ticket_dashboard.domain import events, identifiers
from codex_ticket_dashboard.domain import status as states
from codex_ticket_dashboard.domain.source_metadata import McpContextWitness
from codex_ticket_dashboard.ingest import payload_models as models
from codex_ticket_dashboard.mcp import schemas
from codex_ticket_dashboard.storage import spool
from codex_ticket_dashboard.storage.models import RecordType


class EventRecorder:
    """Convert one typed tool request into exactly one persisted event."""

    _writer: spool.SpoolWriter

    def __init__(self, writer: spool.SpoolWriter) -> None:
        """Bind one protected atomic spool writer."""
        self._writer = writer

    def record(
        self, request: schemas.McpRequest, *, witness: McpContextWitness | None = None
    ) -> mcp_api.AdmissionReceipt:
        """Build and atomically admit one event or raise a protocol tool error."""
        match request:
            case schemas.TicketPreflightRequest() as value:
                ticket_id = value.ticket_id or identifiers.new_ticket_id()
                payload = _ticket_payload(value)
                event_type = (
                    events.EventType.TICKET_LINKED_TO_THREAD
                    if value.disposition == "LINK_EXISTING"
                    else events.EventType.TICKET_CREATED
                )
                facts = mcp_api.AdmissionFacts(
                    event_type, events.ActorType.CODEX, value.context, ticket_id, None, "TICKET"
                )
            case schemas.TaskUpsertRequest() as value:
                work_item_id = value.work_item_id or identifiers.new_work_item_id()
                payload = _work_item_payload(value)
                event_type = (
                    events.EventType.UNCLASSIFIED_ACTIVITY_CREATED
                    if value.kind == "UNCLASSIFIED"
                    else events.EventType.WORK_ITEM_CREATED
                    if value.work_item_id is None
                    else events.EventType.WORK_ITEM_UPDATED
                )
                actor = (
                    events.ActorType.USER
                    if value.status
                    in {states.WorkItemStatus.CANCELLED, states.WorkItemStatus.SUPERSEDED}
                    else events.ActorType.CODEX
                )
                facts = mcp_api.AdmissionFacts(
                    event_type, actor, value.context, value.ticket_id, work_item_id, "WORK_ITEM"
                )
            case schemas.TicketStatusUpdateRequest() as value:
                payload = _status_payload(value)
                actor = (
                    events.ActorType.USER
                    if value.authority == states.StatusAuthority.USER_EXPLICIT.value
                    else events.ActorType.CODEX
                )
                facts = mcp_api.AdmissionFacts(
                    events.EventType.STATUS_CHANGED,
                    actor,
                    value.context,
                    value.ticket_id,
                    None,
                    "TICKET",
                )
            case schemas.TicketUserDecisionRequest() as value:
                payload = models.UserDecisionPayload(
                    authority=states.StatusAuthority.USER_EXPLICIT,
                    source_turn_id=value.source_turn_id,
                    decision=value.decision,
                    decision_summary=value.decision_summary,
                    content_type=value.content_type,
                    content_length=value.content_length,
                    content_digest=value.content_digest,
                )
                facts = mcp_api.AdmissionFacts(
                    events.EventType.USER_DECISION_RECORDED,
                    events.ActorType.USER,
                    value.context,
                    value.ticket_id,
                    None,
                    "DECISION",
                )
            case schemas.TicketTurnSummaryRequest() as value:
                payload = _summary_payload(value)
                facts = mcp_api.AdmissionFacts(
                    events.EventType.TURN_SUMMARIZED,
                    events.ActorType.CODEX,
                    value.context,
                    value.ticket_id,
                    None,
                    "TICKET",
                )
            case schemas.GitGateReportRequest() as value:
                payload = models.GitGatePayload.model_validate(
                    {
                        "authority": states.StatusAuthority.CODEX_RESULT,
                        **value.model_dump(exclude={"context", "ticket_id"}),
                    }
                )
                facts = mcp_api.AdmissionFacts(
                    events.EventType.GIT_GATE_REPORTED,
                    events.ActorType.CODEX,
                    value.context,
                    value.ticket_id,
                    None,
                    "TICKET",
                )
            case schemas.WikiUpdateRecordRequest() as value:
                payload = models.WikiGatePayload.model_validate(
                    {
                        "authority": states.StatusAuthority.CODEX_RESULT,
                        **value.model_dump(mode="json", exclude={"context", "ticket_id"}),
                    }
                )
                facts = mcp_api.AdmissionFacts(
                    events.EventType.WIKI_GATE_REPORTED,
                    events.ActorType.CODEX,
                    value.context,
                    value.ticket_id,
                    None,
                    "TICKET",
                )
            case unreachable:
                assert_never(unreachable)
        return mcp_api.admit_event(self._writer, request, payload, facts, witness=witness)


def _ticket_payload(
    request: schemas.TicketPreflightRequest,
) -> models.TicketPayload | models.TicketLinkPayload:
    if request.disposition == "LINK_EXISTING":
        return models.TicketLinkPayload(
            authority=states.StatusAuthority.CODEX_PREFLIGHT,
            disposition="LINK_EXISTING",
            classification=request.classification,
            goal=request.goal,
            non_goals=request.non_goals,
            acceptance_criteria=request.acceptance_criteria,
            declared_git_requirement=request.declared_git_requirement,
            declared_wiki_requirement=request.declared_wiki_requirement,
        )
    record_type = {
        "TASK": RecordType.WORK_TICKET,
        "DISCUSSION": RecordType.DISCUSSION_LOG,
        "UNCLASSIFIED": RecordType.UNCLASSIFIED,
    }[request.classification]
    return models.TicketPayload(
        authority=states.StatusAuthority.CODEX_PREFLIGHT,
        title=request.goal[:300],
        record_type=record_type,
        status=states.TicketStatus.PLANNED,
        needs_triage=request.classification == "UNCLASSIFIED",
        summary=request.goal,
        next_step=request.acceptance_criteria[0],
        disposition=request.disposition,
        classification=request.classification,
        goal=request.goal,
        non_goals=request.non_goals,
        acceptance_criteria=request.acceptance_criteria,
        declared_git_requirement=request.declared_git_requirement,
        declared_wiki_requirement=request.declared_wiki_requirement,
    )


def _work_item_payload(
    request: schemas.TaskUpsertRequest,
) -> models.WorkItemPayload | models.UnclassifiedActivityPayload:
    authority = (
        states.StatusAuthority.USER_EXPLICIT
        if request.status in {states.WorkItemStatus.CANCELLED, states.WorkItemStatus.SUPERSEDED}
        else states.StatusAuthority.CODEX_RESULT
        if request.status is states.WorkItemStatus.RESULT_REPORTED
        else states.StatusAuthority.CODEX_EXECUTION
    )
    payload_data = {
        "authority": authority,
        "parent_work_item_id": request.parent_work_item_id,
        "kind": request.kind,
        "status": request.status,
        "summary": request.title,
        "title": request.title,
        "acceptance_criteria": request.acceptance_criteria,
        "user_decision_event_id": request.user_decision_event_id,
    }
    if request.kind == "UNCLASSIFIED":
        return models.UnclassifiedActivityPayload.model_validate(payload_data)
    return models.WorkItemPayload.model_validate(payload_data)


def _status_payload(request: schemas.TicketStatusUpdateRequest) -> models.StatusPayload:
    return models.StatusPayload.model_validate(
        {
            "authority": states.StatusAuthority(request.authority),
            **request.model_dump(exclude={"context", "ticket_id", "authority"}),
        }
    )


def _summary_payload(request: schemas.TicketTurnSummaryRequest) -> models.TurnSummaryPayload:
    content = request.model_dump(mode="json", exclude={"context", "ticket_id"})
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return models.TurnSummaryPayload.model_validate(
        {
            "authority": states.StatusAuthority.CODEX_RESULT,
            "content_type": "application/vnd.codex-ticket-summary+json",
            "content_length": len(encoded),
            "content_digest": identifiers.PayloadDigest("sha256:" + sha256(encoded).hexdigest()),
            **content,
        }
    )
