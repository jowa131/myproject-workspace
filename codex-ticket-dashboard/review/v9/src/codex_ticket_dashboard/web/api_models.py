"""Typed, privacy-safe HTTP response models."""

from dataclasses import dataclass
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Reject unknown response fields and keep response data immutable."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class HealthResponse(ApiModel):
    """Expose only service readiness and the current immutable sequence."""

    status: Literal["READY"] = "READY"
    snapshot_high_watermark: int = Field(ge=0)


class ProjectItem(ApiModel):
    """Render a project without local filesystem paths."""

    project_id: str
    label: str
    repo_key: str
    created_seq: int = Field(gt=0)


class ProjectDetail(ProjectItem):
    """Render one project with its current compliance count."""

    compliance_gate_count: int = Field(ge=0)


class TicketItem(ApiModel):
    """Render one ticket's current structured summary."""

    ticket_id: str
    project_id: str
    title: str
    record_type: str
    status: str
    needs_triage: bool
    summary: str
    next_step: str
    created_seq: int = Field(gt=0)


class WorkItem(ApiModel):
    """Render one current work item without source text."""

    work_item_id: str
    parent_work_item_id: str | None
    kind: str
    status: str
    summary: str
    created_seq: int = Field(gt=0)


class ComplianceGate(ApiModel):
    """Render a privacy-safe compliance gate state."""

    gate_id: str
    project_id: str
    ticket_id: str | None
    work_item_id: str | None
    gate_type: str
    requirement: str
    status: str
    created_seq: int = Field(gt=0)


class TicketDetail(TicketItem):
    """Render a ticket's linked structured state."""

    session_ids: tuple[str, ...]
    work_items: tuple[WorkItem, ...]
    compliance_gates: tuple[ComplianceGate, ...]


class TicketEvent(ApiModel):
    """Render immutable event metadata without a payload or transcript."""

    event_id: str
    event_type: str
    occurred_at: str
    actor_type: str
    authority: str
    project_id: str | None
    ticket_id: str
    work_item_id: str | None
    ingest_seq: int = Field(gt=0)


class IngestIssue(ApiModel):
    """Render one redacted collector issue."""

    issue_id: str
    event_id: str | None
    code: str
    field_path: str
    state: str
    created_seq: int = Field(gt=0)


class Page[ResponseItem: ApiModel](ApiModel):
    """Return a bounded, immutable-sequence page."""

    items: tuple[ResponseItem, ...]
    next_cursor: str | None
    has_more: bool
    snapshot_high_watermark: int = Field(ge=0)


class ErrorResponse(ApiModel):
    """Expose a stable error code without request or storage details."""

    code: str


@dataclass(frozen=True, slots=True)
class PageRequest:
    """Represent one bounded, opaque-cursor pagination request."""

    limit: int
    cursor: str | None


@dataclass(frozen=True, slots=True)
class TicketFilters:
    """Represent independently validated ticket list filters."""

    status: str | None
    project_id: str | None
    needs_triage: bool | None
