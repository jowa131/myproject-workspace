"""One bounded, read-only Stop snapshot plus pending-publish race detection."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.compliance.policy_resolver import GitRequirement, WikiRequirement
from codex_ticket_dashboard.compliance.project_registry import ProjectResolution
from codex_ticket_dashboard.domain.events import EventOrigin
from codex_ticket_dashboard.ingest.payloads import parse_payload
from codex_ticket_dashboard.ingest.recovery import read_safe_event, scan_spool
from codex_ticket_dashboard.lifecycle.completeness import AppliedRequirements
from codex_ticket_dashboard.lifecycle.contracts import stop_claim_key
from codex_ticket_dashboard.lifecycle.initial_preflight import initial_absence
from codex_ticket_dashboard.lifecycle.normalization import ObservationError
from codex_ticket_dashboard.lifecycle.review_evidence import review_is_verified
from codex_ticket_dashboard.storage.path_security import DataRootPaths, validate_secure_path
from codex_ticket_dashboard.storage.readonly_observation import read_observation_database
from codex_ticket_dashboard.storage.related_recording import (
    RelatedRecording,
    read_related_recording,
)
from codex_ticket_dashboard.storage.turn_recording import TurnKey, TurnRecording

_COUNT: Final[TypeAdapter[tuple[int]]] = TypeAdapter(tuple[int])
_POLICY: Final[TypeAdapter[tuple[GitRequirement, WikiRequirement, str] | None]] = TypeAdapter(
    tuple[GitRequirement, WikiRequirement, str] | None
)
MAX_PENDING_CANDIDATES: Final = 256


@dataclass(frozen=True, slots=True)
class StopSnapshot:
    """Applied facts stay distinct from pending and from original-turn budget evidence."""

    recording: TurnRecording
    pending_types: frozenset[str]
    stable: bool
    budget_recorded: bool
    high_watermark: int
    review_verified: bool
    requirements: AppliedRequirements | None
    ticket_project_id: str | None
    related: RelatedRecording
    initial_preflight: bool = False


def read_stop_snapshot(
    paths: DataRootPaths, key: TurnKey, initial_identity: ProjectResolution | None = None,
) -> StopSnapshot:
    """Do not create SQLite or regard a moved/malformed pending file as absence."""
    with read_observation_database(paths.data / "dashboard.sqlite3", paths.root) as connection:
        watermark = _COUNT.validate_python(
            connection.execute(
                "SELECT last_seq FROM ingest_sequences WHERE singleton=1",
            ).fetchone()
        )[0]
        related = read_related_recording(connection, key, watermark)
        recording = related.combined
        original = related.original_key
        budget = (
            _COUNT.validate_python(
                connection.execute(
                    "SELECT COUNT(*) FROM lifecycle_stop_claims WHERE claim_key=?",
                    (stop_claim_key(original.source_host, original.thread_id, original.turn_id),),
                ).fetchone()
            )[0]
            > 0
        )
        review_verified = review_is_verified(connection, recording, watermark)
        tickets = {fact.ticket_id for fact in recording.facts if fact.ticket_id is not None}
        policy = (
            None
            if len(tickets) != 1
            else _POLICY.validate_python(
                connection.execute(
                    """SELECT p.git_authority,p.wiki_authority,t.project_id FROM tickets t
                    JOIN project_policies p ON p.project_id=t.project_id WHERE t.id=?""",
                    (next(iter(tickets)),),
                ).fetchone()
            )
        )
        requirements = None if policy is None else AppliedRequirements(policy[0], policy[1])
        pending = _pending_types(paths, original)
        if related.correction_key is not None:
            pending |= _pending_types(paths, related.correction_key)
        initial = (
            initial_identity is not None and not recording.facts and not pending
            and related.original_key == key and related.correction_key is None
            and not related.relation_unverified
            and initial_absence(connection, paths, key, initial_identity)
        )
        _ = connection.execute("COMMIT")
        current = _COUNT.validate_python(
            connection.execute(
                "SELECT last_seq FROM ingest_sequences WHERE singleton=1",
            ).fetchone()
        )[0]
        return StopSnapshot(
            recording,
            pending,
            current == watermark,
            budget,
            watermark,
            review_verified,
            requirements,
            None if policy is None else policy[2],
            related,
            initial,
        )


def _pending_types(paths: DataRootPaths, key: TurnKey) -> frozenset[str]:
    prefix = sha256(key.turn_id.encode()).hexdigest()[:24] + "__"
    candidates = tuple(path for path in scan_spool(paths) if path.name.startswith(prefix))
    if len(candidates) > MAX_PENDING_CANDIDATES:
        raise ObservationError(code="ADMISSION_UNVERIFIED")
    types: set[str] = set()
    for path in candidates:
        _ = validate_secure_path(path, paths.root)
        event = read_safe_event(path)
        if event is None:
            raise ObservationError(code="ADMISSION_UNVERIFIED")
        witness = event.mcp_context
        if (
            event.origin is EventOrigin.MCP_TOOL
            and witness is not None
            and (witness.source_host, witness.thread_id, witness.turn_id, witness.parent_thread_id)
            == (key.source_host, key.thread_id, key.turn_id, key.parent_thread_id)
        ):
            _ = parse_payload(event.event_type, event.payload.root)
            types.add(event.event_type.value)
    return frozenset(types)
