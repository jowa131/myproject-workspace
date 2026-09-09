"""Typed SQLite admission and projection boundaries."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum, unique
from pathlib import Path
from typing import Annotated, ClassVar, Literal, override

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    RootModel,
    model_validator,
)
from pydantic_core import PydanticCustomError

from codex_ticket_dashboard.domain import events, identifiers, redaction
from codex_ticket_dashboard.domain.status import StatusAuthority, TicketStatus

ValidatedTurnId = Annotated[identifiers.TurnId, Field(min_length=1, max_length=128)]
StableEntityId = Annotated[str, Field(pattern=r"^[a-z]+_[A-Za-z0-9_-]{1,128}$")]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
StableCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")]
Summary = Annotated[str, Field(max_length=4000)]
_PAYLOAD_PRIVACY_ERROR = "payload_privacy_rejected"


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """Validated settings for one local SQLite database."""

    path: Path
    busy_timeout_ms: int = 5_000
    migrations_path: Path | None = None


@dataclass(frozen=True, slots=True)
class MigrationVersionError(RuntimeError):
    """Render migration version failures without database content."""

    version: int
    code: ClassVar[str]

    @override
    def __str__(self) -> str:
        return f"{self.code}: version={self.version}"


class MigrationChecksumMismatchError(MigrationVersionError):
    """Signal that an applied migration no longer matches its source."""

    code: ClassVar[Literal["MIGRATION_CHECKSUM_MISMATCH"]] = "MIGRATION_CHECKSUM_MISMATCH"


class UnsupportedSchemaVersionError(MigrationVersionError):
    """Signal that the database is newer than this executable."""

    code: ClassVar[Literal["UNSUPPORTED_SCHEMA_VERSION"]] = "UNSUPPORTED_SCHEMA_VERSION"


class MigrationFailedError(MigrationVersionError):
    """Report a migration failure without retaining SQL or database text."""

    code: ClassVar[Literal["MIGRATION_FAILED"]] = "MIGRATION_FAILED"


@dataclass(frozen=True, slots=True)
class InvalidDatabaseConfigError(ValueError):
    """Report an invalid local database setting."""

    field_path: str
    code: Literal["INVALID_DATABASE_CONFIG"] = "INVALID_DATABASE_CONFIG"

    @override
    def __str__(self) -> str:
        return f"{self.code}: field={self.field_path}"


@dataclass(frozen=True, slots=True)
class Migration:
    """One immutable migration source and checksum."""

    version: int
    name: str
    checksum: str
    sql: str


class BoundaryModel(BaseModel):
    """Reject unknown fields and omit rejected values from validation errors."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
        revalidate_instances="always",
    )


class CanonicalPayload(RootModel[dict[str, JsonValue]]):
    """Typed JSON object screened by the shared recursive privacy policy."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, allow_inf_nan=False)

    @model_validator(mode="after")
    def _reject_private_content(self) -> "CanonicalPayload":
        result = redaction.parse_structured_summary_json(self.model_dump_json())
        match result:
            case redaction.SummaryRejected(code=code, field_path=path):
                if code != "SUMMARY_SCHEMA_INVALID":
                    raise PydanticCustomError(
                        _PAYLOAD_PRIVACY_ERROR,
                        "{code}: field={path}",
                        {"code": code, "path": path},
                    )
            case redaction.SummaryAccepted():
                pass
        return self


class EventAdmission(BoundaryModel):
    """Metadata admitted from a persisted, already-redacted spool event."""

    event_id: events.ValidatedEventId
    idempotency_key: events.ValidatedIdempotencyKey
    payload_digest: events.ValidatedPayloadDigest
    event_type: events.EventType
    schema_version: Annotated[int, Field(gt=0)] = 1
    occurred_at: AwareDatetime
    received_at: AwareDatetime | None
    actor_type: events.ActorType
    origin: events.EventOrigin
    authority: StatusAuthority
    project_observation_id: events.ValidatedProjectObservationId
    project_id: events.ValidatedProjectId | None
    project_resolution_state: events.ProjectResolutionState
    repo_key: events.ValidatedRepoKey | None
    session_id: events.ValidatedSessionId
    turn_id: ValidatedTurnId | None
    ticket_id: events.ValidatedTicketId | None
    work_item_id: events.ValidatedWorkItemId | None
    causation_event_id: events.ValidatedEventId | None
    depends_on_event_ids: tuple[events.ValidatedEventId, ...]
    payload: CanonicalPayload


class ProjectChange(BoundaryModel):
    """One project projection version."""

    project_id: events.ValidatedProjectId
    label: Annotated[str, Field(min_length=1, max_length=200)]
    logical_root_key: Annotated[str, Field(min_length=1, max_length=256)]
    repo_key: Annotated[str, Field(pattern=r"^repo_[A-Za-z0-9_-]{1,128}$")]
    identity_source: Annotated[str, Field(pattern="^REGISTRY$")]
    identity_source_hash: Digest


@unique
class RecordType(StrEnum):
    """Ticket record classifications."""

    WORK_TICKET = "WORK_TICKET"
    DISCUSSION_LOG = "DISCUSSION_LOG"
    UNCLASSIFIED = "UNCLASSIFIED"


class TicketChange(BoundaryModel):
    """One ticket projection version."""

    ticket_id: events.ValidatedTicketId
    project_id: events.ValidatedProjectId
    title: Annotated[str, Field(min_length=1, max_length=300)]
    record_type: RecordType
    status: TicketStatus
    needs_triage: bool
    summary: Summary
    next_step: Summary
    closed_at: AwareDatetime | None = None
    closed_reason: Annotated[str, Field(max_length=500)] | None = None


@unique
class GateType(StrEnum):
    """Supported compliance gate types."""

    GIT = "GIT"
    WIKI = "WIKI"


@unique
class GateRequirement(StrEnum):
    """Compliance gate requirement levels."""

    REQUIRED = "REQUIRED"
    ADVISORY = "ADVISORY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@unique
class GateStatus(StrEnum):
    """Compliance projection states."""

    PENDING = "PENDING"
    SATISFIED = "SATISFIED"
    STATUS_ONLY = "STATUS-ONLY"
    COMMIT_PENDING = "COMMIT-PENDING"
    PUSH_PENDING = "PUSH-PENDING"
    UPDATE_PENDING = "UPDATE-PENDING"
    UNVERIFIED = "UNVERIFIED"
    BLOCKED = "BLOCKED"
    COMPLIANCE_INCOMPLETE = "COMPLIANCE_INCOMPLETE"
    NOT_APPLICABLE = "N/A"


class ComplianceGateChange(BoundaryModel):
    """One Git or Wiki gate projection version."""

    gate_id: StableEntityId
    project_id: events.ValidatedProjectId
    ticket_id: events.ValidatedTicketId | None
    work_item_id: events.ValidatedWorkItemId | None
    gate_type: GateType
    requirement: GateRequirement
    status: GateStatus
    evidence_ref: Annotated[str, Field(max_length=500)] | None
    evidence_hash: Digest | None


@unique
class IngestIssueState(StrEnum):
    """Collector issue lifecycle states."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class IngestIssueChange(BoundaryModel):
    """One privacy-safe ingest issue projection version."""

    issue_id: StableEntityId
    event_id: events.ValidatedEventId | None
    code: StableCode
    field_path: Annotated[str, Field(min_length=1, max_length=200)]
    state: IngestIssueState


type ProjectionChange = ProjectChange | TicketChange | ComplianceGateChange | IngestIssueChange


@dataclass(frozen=True, slots=True)
class ProjectionWrite:
    """One sequence-stamped projection mutation."""

    ingest_seq: int
    occurred_at: datetime
    change: ProjectionChange


@dataclass(frozen=True, slots=True)
class ReceiptRecord:
    """Applied receipt returned by idempotent admission."""

    event_id: identifiers.EventId
    idempotency_key: identifiers.IdempotencyKey
    payload_digest: identifiers.PayloadDigest
    ingest_seq: int
    state: str = "APPLIED"


@dataclass(frozen=True, slots=True)
class ProjectSnapshot:
    """Project projection at a fixed ingest watermark."""

    project_id: identifiers.ProjectId
    label: str
    logical_root_key: str
    repo_key: str
    identity_source: str
    identity_source_hash: str
    created_seq: int
    version: int


@dataclass(frozen=True, slots=True)
class TicketSnapshot:
    """Ticket projection at a fixed ingest watermark."""

    ticket_id: identifiers.TicketId
    project_id: identifiers.ProjectId
    title: str
    record_type: str
    status: str
    needs_triage: bool
    summary: str
    next_step: str
    created_at: datetime
    updated_at: datetime
    created_seq: int
    closed_at: datetime | None
    closed_reason: str | None
    version: int


@dataclass(frozen=True, slots=True)
class ComplianceGateSnapshot:
    """Compliance gate projection at a fixed ingest watermark."""

    gate_id: str
    status: str
    created_seq: int
    version: int


@dataclass(frozen=True, slots=True)
class IngestIssueSnapshot:
    """Ingest issue projection at a fixed ingest watermark."""

    issue_id: str
    state: str
    created_seq: int
    version: int
