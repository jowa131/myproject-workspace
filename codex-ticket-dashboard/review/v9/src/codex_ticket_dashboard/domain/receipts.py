"""Ingest and archive receipt boundary contract."""

from dataclasses import dataclass
from enum import StrEnum, unique
from typing import Annotated, ClassVar, Literal, Self, assert_never, override

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from codex_ticket_dashboard.domain.identifiers import (
    ArchivePayloadSha256,
    EventId,
    PayloadDigest,
    parse_archive_payload_sha256,
    parse_event_id,
    parse_payload_digest,
)

ValidatedEventId = Annotated[EventId, AfterValidator(parse_event_id)]
ValidatedArchivePayloadSha256 = Annotated[
    ArchivePayloadSha256,
    AfterValidator(parse_archive_payload_sha256),
]
ValidatedPayloadDigest = Annotated[PayloadDigest, AfterValidator(parse_payload_digest)]
ArchiveErrorCode = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,79}$")]


@unique
class ReceiptState(StrEnum):
    """Final ingest receipt states."""

    RECEIVED = "RECEIVED"
    PENDING_IDENTITY = "PENDING_IDENTITY"
    PENDING_DEPENDENCY = "PENDING_DEPENDENCY"
    APPLIED = "APPLIED"
    DEPENDENCY_FAILED = "DEPENDENCY_FAILED"
    REJECTED = "REJECTED"


@unique
class ProjectionState(StrEnum):
    """Spool admission projection state."""

    PENDING = "PENDING"


@unique
class ArchiveState(StrEnum):
    """Two-phase success archive states."""

    PENDING = "PENDING"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


type ReceiptContractCode = Literal[
    "DEPENDENCY_FAILURE_PROVENANCE_REQUIRED",
    "ARCHIVE_FIELDS_WITHOUT_STATE",
    "ARCHIVE_PAYLOAD_SHA256_REQUIRED",
    "ARCHIVE_ERROR_CODE_FORBIDDEN",
    "ARCHIVE_ERROR_CODE_REQUIRED",
]


@dataclass(frozen=True, slots=True)
class ReceiptContractError(ValueError):
    """Stable receipt contract error without rejected field content."""

    code: ReceiptContractCode
    field_path: str
    issue_count: Literal[1] = 1

    @override
    def __str__(self) -> str:
        """Return only the stable code, field path, and count."""
        return f"{self.code}: field={self.field_path} count={self.issue_count}"


class IngestReceipt(BaseModel):
    """Final receipt with dependency and two-phase archive evidence."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )

    state: ReceiptState
    event_id: ValidatedEventId
    payload_digest: ValidatedPayloadDigest
    failure_code: str | None
    failed_dependency_event_id: ValidatedEventId | None
    root_failed_dependency_event_id: ValidatedEventId | None
    archive_state: ArchiveState | None
    archive_error_code: ArchiveErrorCode | None
    archive_payload_sha256: ValidatedArchivePayloadSha256 | None

    @model_validator(mode="after")
    def validate_receipt(self) -> Self:
        """Require state-appropriate dependency and archive evidence."""
        self._validate_dependency_failure()
        self._validate_archive_state()
        return self

    def _validate_dependency_failure(self) -> None:
        match self.state:
            case ReceiptState.DEPENDENCY_FAILED:
                required = (
                    self.failure_code,
                    self.failed_dependency_event_id,
                    self.root_failed_dependency_event_id,
                )
                if any(value is None for value in required):
                    raise ReceiptContractError(
                        code="DEPENDENCY_FAILURE_PROVENANCE_REQUIRED",
                        field_path="receipt.dependency",
                    )
            case (
                ReceiptState.RECEIVED
                | ReceiptState.PENDING_IDENTITY
                | ReceiptState.PENDING_DEPENDENCY
                | ReceiptState.APPLIED
                | ReceiptState.REJECTED
            ):
                pass
            case unreachable:
                assert_never(unreachable)

    def _validate_archive_state(self) -> None:
        match self.archive_state:
            case None:
                if self.archive_error_code is not None or self.archive_payload_sha256 is not None:
                    raise ReceiptContractError(
                        code="ARCHIVE_FIELDS_WITHOUT_STATE",
                        field_path="receipt.archive",
                    )
            case ArchiveState.PENDING | ArchiveState.ARCHIVED:
                if self.archive_payload_sha256 is None:
                    raise ReceiptContractError(
                        code="ARCHIVE_PAYLOAD_SHA256_REQUIRED",
                        field_path="archive_payload_sha256",
                    )
                if self.archive_error_code is not None:
                    raise ReceiptContractError(
                        code="ARCHIVE_ERROR_CODE_FORBIDDEN",
                        field_path="archive_error_code",
                    )
            case ArchiveState.FAILED:
                if self.archive_payload_sha256 is None:
                    raise ReceiptContractError(
                        code="ARCHIVE_PAYLOAD_SHA256_REQUIRED",
                        field_path="archive_payload_sha256",
                    )
                if self.archive_error_code is None:
                    raise ReceiptContractError(
                        code="ARCHIVE_ERROR_CODE_REQUIRED",
                        field_path="archive_error_code",
                    )
            case unreachable:
                assert_never(unreachable)
