"""Atomic original-turn budget and immutable accepted Stop correction instructions."""

import json
from dataclasses import dataclass
from typing import Final

from pydantic import ValidationError

from codex_ticket_dashboard.compliance.project_registry import ProjectResolution
from codex_ticket_dashboard.domain.events import EventEnvelope
from codex_ticket_dashboard.lifecycle.admission import admit_observation, observation_envelope
from codex_ticket_dashboard.lifecycle.completeness import StopAssessment, assess_turn
from codex_ticket_dashboard.lifecycle.continuation import ContinuationClaim, consume_claim_locked
from codex_ticket_dashboard.lifecycle.contracts import LifecyclePayload, StopClaim, stop_claim_key
from codex_ticket_dashboard.lifecycle.initial_preflight import initial_response
from codex_ticket_dashboard.lifecycle.normalization import NormalizedHook, ObservationError
from codex_ticket_dashboard.lifecycle.receipts import canonical_intent_locked, read_intent_locked
from codex_ticket_dashboard.lifecycle.stop_reading import StopSnapshot, read_stop_snapshot
from codex_ticket_dashboard.storage.locks import AdmissionLock
from codex_ticket_dashboard.storage.path_security import DataRootPaths, validate_secure_path
from codex_ticket_dashboard.storage.turn_recording import TurnKey

_DERIVED: Final = frozenset({"coverage", "mcp_readiness", "missing_requirements", "stop_claim"})


@dataclass(frozen=True, slots=True)
class PreparedStop:
    """Prepared intent and an output that is forbidden before accepted publication."""

    event: EventEnvelope[LifecyclePayload]
    response: str | None


def observe_stop(
    paths: DataRootPaths, hook: NormalizedHook, identity: ProjectResolution
) -> str | None:
    """Return one correction instruction only after protected Stop publication succeeds."""
    _ = validate_secure_path(paths.admission_lock, paths.root)
    with AdmissionLock(paths.admission_lock):
        prepared = _prepare_locked(paths, hook, identity)
    _ = admit_observation(paths, prepared.event)
    return prepared.response


def _prepare_locked(
    paths: DataRootPaths,
    hook: NormalizedHook,
    identity: ProjectResolution,
) -> PreparedStop:
    base = observation_envelope(hook.payload, identity)
    existing = read_intent_locked(paths, base)
    if existing is not None:
        excluded = {"occurred_at", "received_at", "payload_digest", "payload"}
        if existing.model_dump(exclude=excluded) != base.model_dump(
            exclude=excluded
        ) or existing.payload.model_dump(exclude=set(_DERIVED)) != base.payload.model_dump(
            exclude=set(_DERIVED)
        ):
            raise ObservationError(code="IDEMPOTENCY_PAYLOAD_COLLISION")
        return PreparedStop(existing, None)
    snapshot, assessment = _assess(paths, hook, identity)
    claim = None
    response = None
    if (
        snapshot is not None
        and snapshot.stable
        and not snapshot.budget_recorded
        and assessment.request_eligible
        and hook.stop_hook_active is False
        and hook.payload.turn_id is not None
        and identity.project_id is not None
    ):
        claim = ContinuationClaim(
            claim_key=stop_claim_key(base.payload.source_host, base.session_id, base.turn_id or ""),
            source_host=base.payload.source_host,
            thread_id=base.session_id,
            original_turn_id=hook.payload.turn_id,
            claim_event_id=base.event_id,
            request_kind="INITIAL_PREFLIGHT" if snapshot.initial_preflight else "TICKET_CORRECTION",
        )
        if consume_claim_locked(paths, claim):
            if claim.request_kind == "INITIAL_PREFLIGHT":
                response = initial_response(claim)
            else:
                tickets = {
                    fact.ticket_id
                    for fact in snapshot.recording.facts if fact.ticket_id is not None
                }
                response = _response(claim, next(iter(tickets)), assessment)
    recorded_claim = (
        _observed_claim(snapshot, hook)
        if claim is None or claim.request_kind == "INITIAL_PREFLIGHT"
        else StopClaim(
            claim_key=claim.claim_key,
            original_turn_id=claim.original_turn_id,
            state="CLAIMED",
        )
    )
    changes = {
        "coverage": "GAP_DETECTED"
        if assessment.state == "MISSING"
        else "OBSERVED"
        if assessment.state == "COMPLETE"
        else "UNVERIFIED",
        "mcp_readiness": "READY"
        if snapshot is not None and snapshot.recording.facts
        else "UNVERIFIED",
        "missing_requirements": assessment.missing_requirements,
        "stop_claim": None if recorded_claim is None else recorded_claim.model_dump(),
    }
    payload = LifecyclePayload.model_validate(hook.payload.model_dump() | changes)
    event = canonical_intent_locked(paths, observation_envelope(payload, identity))
    return PreparedStop(event, response)


def _assess(
    paths: DataRootPaths, hook: NormalizedHook, identity: ProjectResolution
) -> tuple[StopSnapshot | None, StopAssessment]:
    if hook.payload.turn_id is None:
        return None, StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    key = TurnKey(
        hook.payload.source_host,
        hook.payload.thread_id,
        hook.payload.turn_id,
        hook.payload.parent_thread_id,
    )
    try:
        snapshot = read_stop_snapshot(paths, key, identity)
    except (OSError, ValueError, ValidationError):
        return None, StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    if (
        not snapshot.stable
        or snapshot.related.relation_unverified
        or (hook.stop_hook_active is not False and snapshot.related.correction_key != key)
    ):
        return snapshot, StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    if snapshot.initial_preflight:
        return snapshot, StopAssessment("MISSING", ("PREFLIGHT",))
    if snapshot.ticket_project_id != identity.project_id:
        return snapshot, StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    return snapshot, assess_turn(
        snapshot.recording,
        snapshot.pending_types,
        review_verified=snapshot.review_verified,
        requirements=snapshot.requirements,
        original=snapshot.related.original,
    )


def _observed_claim(snapshot: StopSnapshot | None, hook: NormalizedHook) -> StopClaim | None:
    if snapshot is None or snapshot.related.relation_unverified:
        return None
    related = snapshot.related
    correction = related.correction_key
    if correction is None or correction.turn_id != hook.payload.turn_id:
        return None
    original = related.original_key
    return StopClaim(
        claim_key=stop_claim_key(original.source_host, original.thread_id, original.turn_id),
        original_turn_id=original.turn_id,
        continuation_turn_id=correction.turn_id,
        state="CONTINUATION_OBSERVED",
    )


def _response(claim: ContinuationClaim, ticket_id: str, assessment: StopAssessment) -> str:
    instruction = {
        "code": "CTD_CORRECTION_V1",
        "claim_event_id": claim.claim_event_id,
        "original_turn_id": claim.original_turn_id,
        "ticket_id": ticket_id,
        "missing_requirements": assessment.missing_requirements,
        "instruction": (
            "Record only the listed missing structured records for the existing ticket. "
            "Use this claim_event_id as context.causation_event_id on each correction MCP call. "
            "Use the current official turn; preserve original records and user decision authority."
        ),
    }
    return json.dumps(
        {"decision": "block", "reason": json.dumps(instruction, separators=(",", ":"))}
    )
