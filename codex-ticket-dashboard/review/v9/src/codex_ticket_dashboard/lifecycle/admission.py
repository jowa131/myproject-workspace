"""Deterministic observer envelope construction and publication orchestration."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal, assert_never
from uuid import UUID

from codex_ticket_dashboard.compliance.project_registry import ProjectResolution
from codex_ticket_dashboard.domain.events import ActorType, EventEnvelope, EventOrigin, EventType
from codex_ticket_dashboard.domain.identifiers import EventId, PayloadDigest, SessionId, TurnId
from codex_ticket_dashboard.lifecycle.contracts import (
    HOOK_EVENT_TYPES,
    LifecyclePayload,
    lifecycle_idempotency_key,
)
from codex_ticket_dashboard.lifecycle.normalization import ObservationError
from codex_ticket_dashboard.lifecycle.receipts import accepted_copy_exists, canonical_intent
from codex_ticket_dashboard.storage.path_security import DataRootPaths
from codex_ticket_dashboard.storage.spool import (
    SpoolAccepted,
    SpoolCollision,
    SpoolExisting,
    SpoolWriter,
)


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    """Successful durable-event outcome only, never an intent-only receipt."""

    code: Literal["ACCEPTED", "IDEMPOTENT_EXISTING"]
    event_id: EventId


def observation_envelope(
    payload: LifecyclePayload,
    resolution: ProjectResolution,
) -> EventEnvelope[LifecyclePayload]:
    """Create a stable event ID; receipt reuse owns byte-identical retry timestamps."""
    key = lifecycle_idempotency_key(payload)
    event_id = EventId(
        "evt_" + str(UUID(bytes=bytes.fromhex(key.removeprefix("sha256:"))[:16], version=4))
    )
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return EventEnvelope[LifecyclePayload](
        schema_version=1,
        event_id=event_id,
        event_type=EventType(HOOK_EVENT_TYPES[payload.hook_event]),
        occurred_at=datetime.now(UTC),
        received_at=None,
        actor_type=ActorType.OBSERVER,
        origin=EventOrigin.HOOK,
        project_observation_id=resolution.observation_id,
        project_id=resolution.project_id,
        project_resolution_state=resolution.state,
        repo_key=resolution.repo_key,
        session_id=SessionId(payload.thread_id),
        turn_id=None if payload.turn_id is None else TurnId(payload.turn_id),
        ticket_id=None,
        work_item_id=None,
        causation_event_id=None,
        depends_on_event_ids=(),
        payload=payload,
        idempotency_key=key,
        payload_digest=PayloadDigest("sha256:" + sha256(canonical.encode()).hexdigest()),
    )


def admit_observation(
    paths: DataRootPaths,
    event: EventEnvelope[LifecyclePayload],
) -> AdmissionResult:
    """Publish canonical intent without treating an unpublished receipt as success."""
    canonical = canonical_intent(paths, event)
    if accepted_copy_exists(paths, canonical):
        return AdmissionResult("IDEMPOTENT_EXISTING", canonical.event_id)
    result = SpoolWriter(paths).write(canonical)
    match result:
        case SpoolAccepted():
            return AdmissionResult("ACCEPTED", result.event_id)
        case SpoolExisting():
            return AdmissionResult("IDEMPOTENT_EXISTING", result.event_id)
        case SpoolCollision():
            raise ObservationError(code="IDEMPOTENCY_PAYLOAD_COLLISION")
        case unreachable:
            assert_never(unreachable)
