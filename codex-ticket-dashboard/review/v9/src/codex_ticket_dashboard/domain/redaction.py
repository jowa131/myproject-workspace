"""Structure-only summary parsing with fail-closed privacy rejection."""

import re
from dataclasses import dataclass
from typing import Annotated, ClassVar, Final, Literal, assert_never, override

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    TypeAdapter,
    ValidationError,
)

from codex_ticket_dashboard.domain.identifiers import (
    PayloadDigest,
    WorkItemId,
    parse_work_item_id,
)
from codex_ticket_dashboard.domain.status import TicketStatus

MAX_SUMMARY_BYTES: Final = 16_384
MAX_FIELD_CHARS: Final = 2_000
MAX_ITEM_CHARS: Final = 512
MAX_LIST_ITEMS: Final = 32

type RejectionCode = Literal[
    "SUMMARY_SIZE_EXCEEDED",
    "SUMMARY_SCHEMA_INVALID",
    "FORBIDDEN_RAW_FIELD",
    "CREDENTIAL_KEY_REJECTED",
    "CREDENTIAL_VALUE_REJECTED",
    "UNTRUSTED_INSTRUCTION",
]

SummaryText = Annotated[str, Field(min_length=1, max_length=MAX_FIELD_CHARS)]
SummaryItem = Annotated[str, Field(min_length=1, max_length=MAX_ITEM_CHARS)]
SummaryItems = Annotated[tuple[SummaryItem, ...], Field(max_length=MAX_LIST_ITEMS)]
ValidatedWorkItemId = Annotated[WorkItemId, AfterValidator(parse_work_item_id)]

_JSON_ADAPTER: Final[TypeAdapter[JsonValue]] = TypeAdapter(JsonValue)
_KEY_SEPARATOR: Final = re.compile(r"[^a-z0-9]")
_RAW_KEY_FRAGMENTS: Final = (
    "prompt",
    "assistantmessage",
    "transcript",
    "hookoutput",
    "tooloutput",
    "excerpt",
    "rawpayload",
    "rawcontent",
)
_CREDENTIAL_KEY_FRAGMENTS: Final = (
    "token",
    "secret",
    "password",
    "cookie",
    "authorization",
    "apikey",
    "privatekey",
    "credential",
)
_CREDENTIAL_VALUE_PATTERNS: Final = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{16,}"),
    re.compile(r"(?i)\b(?:ghp|github_pat)_[a-z0-9_]{16,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
_INSTRUCTION_PATTERNS: Final = (
    re.compile(r"(?i)ignore (?:all )?(?:previous|prior) instructions"),
    re.compile(r"(?i)reveal .*(?:prompt|secret|credential)"),
    re.compile(r"(?i)<script(?:\s|>)"),
)


@dataclass(frozen=True, slots=True)
class PrivacyViolation:
    """First stable privacy violation found during a bounded tree walk."""

    code: RejectionCode
    field_path: str


@dataclass(frozen=True, slots=True)
class SummaryRejected:
    """Rejected result that retains neither source text nor a source digest."""

    code: RejectionCode
    field_path: str
    issue_count: int

    @override
    def __str__(self) -> str:
        """Return only stable rejection metadata."""
        return f"{self.code}: field={self.field_path} count={self.issue_count}"


class VerificationSummary(BaseModel):
    """Allowlisted verification result inside a structured summary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    check: SummaryItem
    result: SummaryItem
    evidence_ref: SummaryItem


class StructuredSummary(BaseModel):
    """Exact allowlist persisted for request and result display."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    request_feedback_summary: SummaryText
    outcome: SummaryText
    change_surface: SummaryItems
    verification: Annotated[tuple[VerificationSummary, ...], Field(max_length=MAX_LIST_ITEMS)]
    blockers: SummaryItems
    user_decisions: SummaryItems
    next_step: SummaryText
    affected_work_item_ids: Annotated[
        tuple[ValidatedWorkItemId, ...],
        Field(max_length=MAX_LIST_ITEMS),
    ]
    proposed_status: TicketStatus


class SourceMetadata(BaseModel):
    """Only source metadata permitted alongside a structured summary."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    content_type: Annotated[str, Field(min_length=1, max_length=120)]
    content_length: int = Field(ge=0)
    content_digest: Annotated[PayloadDigest, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


@dataclass(frozen=True, slots=True)
class SummaryAccepted:
    """Successfully parsed structure-only summary."""

    summary: StructuredSummary


type SummaryParseResult = SummaryAccepted | SummaryRejected


def _key_violation(key: str, field_path: str) -> PrivacyViolation | None:
    normalized = _KEY_SEPARATOR.sub("", key.casefold())
    if any(fragment in normalized for fragment in _RAW_KEY_FRAGMENTS):
        return PrivacyViolation(code="FORBIDDEN_RAW_FIELD", field_path=field_path)
    if any(fragment in normalized for fragment in _CREDENTIAL_KEY_FRAGMENTS):
        return PrivacyViolation(code="CREDENTIAL_KEY_REJECTED", field_path=field_path)
    return None


def _value_violation(value: str, field_path: str) -> PrivacyViolation | None:
    if any(pattern.search(value) is not None for pattern in _CREDENTIAL_VALUE_PATTERNS):
        return PrivacyViolation(code="CREDENTIAL_VALUE_REJECTED", field_path=field_path)
    if any(pattern.search(value) is not None for pattern in _INSTRUCTION_PATTERNS):
        return PrivacyViolation(code="UNTRUSTED_INSTRUCTION", field_path=field_path)
    return None


def _find_violation(value: JsonValue, field_path: str) -> PrivacyViolation | None:
    match value:
        case None | bool() | int() | float():
            return None
        case str() as text:
            return _value_violation(text, field_path)
        case list() as items:
            return _find_sequence_violation(items, field_path)
        case dict() as mapping:
            return _find_mapping_violation(mapping, field_path)
        case unreachable:
            assert_never(unreachable)


def _find_sequence_violation(
    items: list[JsonValue],
    field_path: str,
) -> PrivacyViolation | None:
    for index, item in enumerate(items):
        violation = _find_violation(item, f"{field_path}[{index}]")
        if violation is not None:
            return violation
    return None


def _find_mapping_violation(
    mapping: dict[str, JsonValue],
    field_path: str,
) -> PrivacyViolation | None:
    for key, item in mapping.items():
        item_path = f"{field_path}.{key}"
        violation = _key_violation(key, item_path)
        if violation is not None:
            return violation
        violation = _find_violation(item, item_path)
        if violation is not None:
            return violation
    return None


def parse_structured_summary_json(raw: str) -> SummaryParseResult:
    """Parse untrusted JSON into the exact summary schema or a redacted rejection."""
    if len(raw.encode("utf-8")) > MAX_SUMMARY_BYTES:
        return SummaryRejected(code="SUMMARY_SIZE_EXCEEDED", field_path="$", issue_count=1)
    try:
        value = _JSON_ADAPTER.validate_json(raw)
    except ValidationError as error:
        return SummaryRejected(
            code="SUMMARY_SCHEMA_INVALID",
            field_path="$",
            issue_count=error.error_count(),
        )
    violation = _find_violation(value, "$")
    if violation is not None:
        return SummaryRejected(
            code=violation.code,
            field_path=violation.field_path,
            issue_count=1,
        )
    try:
        summary = StructuredSummary.model_validate_json(raw)
    except ValidationError as error:
        return SummaryRejected(
            code="SUMMARY_SCHEMA_INVALID",
            field_path="$",
            issue_count=error.error_count(),
        )
    return SummaryAccepted(summary=summary)
