"""Privacy-first rejection and redacted dead-letter persistence."""

import re
import sqlite3
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import ClassVar, Final, Literal, assert_never

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    JsonValue,
    RootModel,
    TypeAdapter,
    ValidationError,
)

from codex_ticket_dashboard.domain.events import (
    EventEnvelope,
    ValidatedEventId,
    ValidatedIdempotencyKey,
    ValidatedPayloadDigest,
)
from codex_ticket_dashboard.domain.identifiers import EventId
from codex_ticket_dashboard.ingest.dependencies import propagate_terminal
from codex_ticket_dashboard.ingest.payload_models import ParsedPayload
from codex_ticket_dashboard.ingest.payloads import parse_payload
from codex_ticket_dashboard.storage.database import Database

_JSON: Final[TypeAdapter[JsonValue]] = TypeAdapter(JsonValue)
_SEQUENCE: Final[TypeAdapter[tuple[int] | None]] = TypeAdapter(tuple[int] | None)
_KEY_SEPARATOR: Final = re.compile(r"[^a-z0-9]")
_FORBIDDEN_KEYS: Final = (
    "prompt",
    "assistantmessage",
    "transcript",
    "hookoutput",
    "tooloutput",
    "excerpt",
    "rawpayload",
    "rawcontent",
    "token",
    "secret",
    "password",
    "cookie",
    "authorization",
    "apikey",
    "privatekey",
    "credential",
)
_FORBIDDEN_VALUES: Final = (
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{16,}"),
    re.compile(r"(?i)\b(?:ghp|github_pat)_[a-z0-9_]{16,}"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class JsonPayload(RootModel[JsonValue]):
    """Validated JSON payload retained only in memory for projection."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, hide_input_in_errors=True)


type CollectedEvent = EventEnvelope[JsonPayload]
_EVENT: Final[TypeAdapter[CollectedEvent]] = TypeAdapter(EventEnvelope[JsonPayload])


class RejectionHeader(BaseModel):
    """Minimum trusted fields needed for a redacted rejection record."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    event_id: ValidatedEventId
    idempotency_key: ValidatedIdempotencyKey
    payload_digest: ValidatedPayloadDigest
    occurred_at: AwareDatetime


@dataclass(frozen=True, slots=True)
class SafeDocument:
    """JSON tree that contains no forbidden key or credential-shaped value."""

    value: JsonValue


@dataclass(frozen=True, slots=True)
class PrivacyRejected:
    """Storage-free privacy rejection with only a field path."""

    field_path: str
    code: Literal["FORBIDDEN_RAW_CONTENT"] = "FORBIDDEN_RAW_CONTENT"


@dataclass(frozen=True, slots=True)
class SafeJsonRejected:
    """Malformed JSON result that intentionally retains no source text."""

    code: Literal["EVENT_SCHEMA_INVALID"] = "EVENT_SCHEMA_INVALID"


type RawInspection = SafeDocument | PrivacyRejected | SafeJsonRejected


def inspect_raw_json(payload: bytes) -> RawInspection:
    """Reject privacy-bearing input before any durable diagnostic is written."""
    try:
        value = _JSON.validate_json(payload)
    except ValidationError:
        return SafeJsonRejected()
    violation = _find_violation(value, "$")
    return SafeDocument(value) if violation is None else violation


def parse_collected_event(value: JsonValue) -> CollectedEvent:
    """Parse one privacy-safe JSON tree into the canonical event envelope."""
    return _EVENT.validate_python(value)


def parse_event_payload(event: CollectedEvent) -> ParsedPayload:
    """Parse the exact event-specific payload allowlist."""
    return parse_payload(event.event_type, event.payload.root)


def parse_rejection_header(value: JsonValue) -> RejectionHeader | None:
    """Parse safe event identity fields without retaining validation details."""
    try:
        return RejectionHeader.model_validate(value)
    except ValidationError:
        return None


def persist_rejection(
    database: Database,
    header: RejectionHeader,
    code: str,
    field_path: str,
) -> tuple[EventId, ...]:
    """Atomically record a safe rejection and terminalize waiting descendants."""
    with database.transaction() as connection:
        sequence = _next_sequence(connection)
        _ = connection.execute(
            """INSERT INTO ingest_receipts(
            idempotency_key,event_id,payload_digest,state,failure_code
            ) VALUES (?,?,?,'REJECTED',?)
            ON CONFLICT(idempotency_key) DO UPDATE SET state='REJECTED',
            failure_code=excluded.failure_code""",
            (header.idempotency_key, header.event_id, header.payload_digest, code),
        )
        _ = connection.execute(
            """INSERT OR REPLACE INTO dead_letters(
            event_id,payload_digest,diagnostic_code,field_path,created_at
            ) VALUES (?,?,?,?,?)""",
            (
                header.event_id,
                header.payload_digest,
                code,
                field_path,
                header.occurred_at.isoformat(),
            ),
        )
        issue_id = "issue_" + sha256(header.event_id.encode()).hexdigest()[:24]
        _ = connection.execute(
            """INSERT INTO ingest_issues VALUES (?,?,?,?,?, ?,1)
            ON CONFLICT(id) DO UPDATE SET code=excluded.code,field_path=excluded.field_path,
            state='OPEN',version=ingest_issues.version+1""",
            (issue_id, header.event_id, code, field_path, "OPEN", sequence),
        )
        return propagate_terminal(connection, header.event_id, code="DEPENDENCY_REJECTED")


def move_to_dead_letter(source: Path, directory: Path) -> Path | None:
    """Move one safe rejected file without overwriting an existing diagnostic."""
    destination = directory / source.name
    if source.parent == directory:
        return source
    if destination.exists():
        return None
    _ = source.rename(destination)
    return destination


def _next_sequence(connection: sqlite3.Connection) -> int:
    row = _SEQUENCE.validate_python(
        connection.execute(
            """UPDATE ingest_sequences SET last_seq=last_seq+1 WHERE singleton=1
            RETURNING last_seq"""
        ).fetchone()
    )
    if row is None:
        message = "INGEST_SEQUENCE_UNAVAILABLE"
        raise sqlite3.DatabaseError(message)
    return int(row[0])


def _find_violation(value: JsonValue, field_path: str) -> PrivacyRejected | None:
    match value:
        case None | bool() | int() | float():
            return None
        case str() as text:
            return (
                PrivacyRejected(field_path)
                if any(pattern.search(text) is not None for pattern in _FORBIDDEN_VALUES)
                else None
            )
        case list() as items:
            return next(
                (
                    violation
                    for index, item in enumerate(items)
                    if (violation := _find_violation(item, f"{field_path}[{index}]"))
                    is not None
                ),
                None,
            )
        case dict() as mapping:
            return _mapping_violation(mapping, field_path)
        case unreachable:
            assert_never(unreachable)


def _mapping_violation(
    mapping: dict[str, JsonValue], field_path: str
) -> PrivacyRejected | None:
    for key, item in mapping.items():
        item_path = f"{field_path}.{key}"
        normalized = _KEY_SEPARATOR.sub("", key.casefold())
        if any(fragment in normalized for fragment in _FORBIDDEN_KEYS):
            return PrivacyRejected(item_path)
        if (violation := _find_violation(item, item_path)) is not None:
            return violation
    return None
