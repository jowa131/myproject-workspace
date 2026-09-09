"""Branded identifier construction and UUIDv4 boundary parsing."""

import re
from dataclasses import dataclass
from typing import Final, Literal, NewType, override
from uuid import RFC_4122, UUID, uuid4

EventId = NewType("EventId", str)
TicketId = NewType("TicketId", str)
WorkItemId = NewType("WorkItemId", str)
ProjectObservationId = NewType("ProjectObservationId", str)
RelationEventId = NewType("RelationEventId", str)
UserDecisionEventId = NewType("UserDecisionEventId", str)
ProjectId = NewType("ProjectId", str)
RepoKey = NewType("RepoKey", str)
SessionId = NewType("SessionId", str)
TurnId = NewType("TurnId", str)
PolicySnapshotId = NewType("PolicySnapshotId", str)
IdempotencyKey = NewType("IdempotencyKey", str)
PayloadDigest = NewType("PayloadDigest", str)
ArchivePayloadSha256 = NewType("ArchivePayloadSha256", str)
UUID_VERSION_4: Final = 4
_PROJECT_ID_PATTERN: Final = re.compile(r"^prj_[A-Za-z0-9_-]{1,128}$")
_REPO_KEY_PATTERN: Final = re.compile(r"^repo_[A-Za-z0-9_-]{1,128}$")
_SESSION_ID_PATTERN: Final = re.compile(r"^thr_[A-Za-z0-9_-]{1,128}$")
_DIGEST_PATTERN: Final = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class InvalidIdentifierError(ValueError):
    """Describe an invalid identifier without retaining the rejected value."""

    code: Literal["INVALID_IDENTIFIER"]
    field_path: str
    issue_count: Literal[1] = 1

    @override
    def __str__(self) -> str:
        """Return a stable, non-sensitive boundary message."""
        return f"{self.code}: field={self.field_path} count={self.issue_count}"


def _parse_uuid4(value: str, prefix: str) -> str:
    if not value.startswith(prefix):
        raise InvalidIdentifierError(code="INVALID_IDENTIFIER", field_path="identifier")
    try:
        parsed = UUID(value.removeprefix(prefix))
    except ValueError as error:
        raise InvalidIdentifierError(
            code="INVALID_IDENTIFIER",
            field_path="identifier",
        ) from error
    if parsed.version != UUID_VERSION_4 or parsed.variant != RFC_4122:
        raise InvalidIdentifierError(code="INVALID_IDENTIFIER", field_path="identifier")
    return value


def parse_event_id(value: str) -> EventId:
    """Parse an event identifier."""
    return EventId(_parse_uuid4(value, "evt_"))


def parse_ticket_id(value: str) -> TicketId:
    """Parse a ticket identifier."""
    return TicketId(_parse_uuid4(value, "tkt_"))


def parse_work_item_id(value: str) -> WorkItemId:
    """Parse a work-item identifier."""
    return WorkItemId(_parse_uuid4(value, "wi_"))


def parse_project_observation_id(value: str) -> ProjectObservationId:
    """Parse a project-observation identifier."""
    return ProjectObservationId(_parse_uuid4(value, "pobs_"))


def parse_relation_event_id(value: str) -> RelationEventId:
    """Parse a turn-relation event identifier."""
    return RelationEventId(_parse_uuid4(value, "rel_"))


def parse_user_decision_event_id(value: str) -> UserDecisionEventId:
    """Parse a user-decision event identifier."""
    return UserDecisionEventId(_parse_uuid4(value, "udec_"))


def parse_project_id(value: str) -> ProjectId:
    """Parse a stable registry project identifier."""
    return ProjectId(_parse_pattern(value, _PROJECT_ID_PATTERN, "project_id"))


def parse_repo_key(value: str) -> RepoKey:
    """Parse a Git common-directory repository key."""
    return RepoKey(_parse_pattern(value, _REPO_KEY_PATTERN, "repo_key"))


def parse_session_id(value: str) -> SessionId:
    """Parse an observed Codex session identifier."""
    return SessionId(_parse_pattern(value, _SESSION_ID_PATTERN, "session_id"))


def parse_idempotency_key(value: str) -> IdempotencyKey:
    """Parse a canonical SHA-256 idempotency key."""
    return IdempotencyKey(_parse_pattern(value, _DIGEST_PATTERN, "idempotency_key"))


def parse_payload_digest(value: str) -> PayloadDigest:
    """Parse a canonical prefixed payload digest."""
    return PayloadDigest(_parse_pattern(value, _DIGEST_PATTERN, "payload_digest"))


def parse_archive_payload_sha256(value: str) -> ArchivePayloadSha256:
    """Parse the unprefixed archive payload SHA-256 field."""
    return ArchivePayloadSha256(_parse_pattern(value, _SHA256_PATTERN, "archive_payload_sha256"))


def _parse_pattern(value: str, pattern: re.Pattern[str], field_path: str) -> str:
    if pattern.fullmatch(value) is None:
        raise InvalidIdentifierError(code="INVALID_IDENTIFIER", field_path=field_path)
    return value


def _new_uuid4(prefix: str) -> str:
    return f"{prefix}{uuid4()}"


def new_event_id() -> EventId:
    """Create an event identifier with a CSPRNG UUIDv4."""
    return EventId(_new_uuid4("evt_"))


def new_ticket_id() -> TicketId:
    """Create a ticket identifier with a CSPRNG UUIDv4."""
    return TicketId(_new_uuid4("tkt_"))


def new_work_item_id() -> WorkItemId:
    """Create a work-item identifier with a CSPRNG UUIDv4."""
    return WorkItemId(_new_uuid4("wi_"))


def new_project_observation_id() -> ProjectObservationId:
    """Create a project-observation identifier with a CSPRNG UUIDv4."""
    return ProjectObservationId(_new_uuid4("pobs_"))


def new_relation_event_id() -> RelationEventId:
    """Create a turn-relation identifier with a CSPRNG UUIDv4."""
    return RelationEventId(_new_uuid4("rel_"))


def new_user_decision_event_id() -> UserDecisionEventId:
    """Create a user-decision identifier with a CSPRNG UUIDv4."""
    return UserDecisionEventId(_new_uuid4("udec_"))
