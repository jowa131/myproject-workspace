"""Collector-only atomic registration and policy bootstrap from verified external authority."""

import json
import sqlite3
from datetime import UTC, datetime
from hashlib import sha256
from typing import Final
from uuid import UUID

from pydantic import BaseModel, TypeAdapter

from codex_ticket_dashboard.compliance.runtime_authority import VerifiedRuntimeAuthority
from codex_ticket_dashboard.compliance.runtime_authority_models import RuntimeAuthorityError
from codex_ticket_dashboard.domain.events import (
    ActorType,
    EventEnvelope,
    EventOrigin,
    EventType,
    ProjectResolutionState,
)
from codex_ticket_dashboard.domain.identifiers import (
    EventId,
    IdempotencyKey,
    PayloadDigest,
    ProjectObservationId,
)
from codex_ticket_dashboard.domain.status import StatusAuthority
from codex_ticket_dashboard.ingest.authority_models import next_ingest_sequence
from codex_ticket_dashboard.ingest.dead_letter import (
    SafeDocument,
    inspect_raw_json,
    parse_collected_event,
    parse_event_payload,
)
from codex_ticket_dashboard.ingest.payload_models import ProjectPayload, ReviewSignalPayload
from codex_ticket_dashboard.ingest.payloads import canonical_payload_json
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.models import ProjectChange, ProjectionWrite

_PROJECT: Final[TypeAdapter[tuple[str, str, str, str, str, int] | None]] = TypeAdapter(
    tuple[str, str, str, str, str, int] | None
)
_POLICY: Final[TypeAdapter[tuple[str, str, str, str, str, str] | None]] = TypeAdapter(
    tuple[str, str, str, str, str, str] | None
)
_COUNT: Final = TypeAdapter(tuple[int])
_BOOTSTRAP_EVENT_COUNT: Final = 2


def _event_id(key: str) -> EventId:
    return EventId("evt_" + str(UUID(bytes=sha256(key.encode()).digest()[:16], version=4)))


def _envelope[PayloadT: BaseModel](
    authority: VerifiedRuntimeAuthority,
    kind: EventType,
    payload: PayloadT,
    parent: EventId | None = None,
) -> EventEnvelope[PayloadT]:
    key = authority.declaration_sha256 + ":" + kind.value
    observation = UUID(bytes=sha256((key + ":observation").encode()).digest()[:16], version=4)
    encoded = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return EventEnvelope[PayloadT](
        schema_version=1,
        event_id=_event_id(key),
        event_type=kind,
        occurred_at=datetime.now(UTC),
        received_at=None,
        actor_type=ActorType.SYSTEM,
        origin=EventOrigin.COLLECTOR,
        project_observation_id=ProjectObservationId("pobs_" + str(observation)),
        project_id=authority.declaration.project_id,
        project_resolution_state=ProjectResolutionState.RESOLVED,
        repo_key=authority.resolution.repo_key,
        session_id=authority.declaration.authorizing_session_id,
        turn_id=None,
        ticket_id=None,
        work_item_id=None,
        causation_event_id=parent,
        depends_on_event_ids=(parent,) if parent is not None else (),
        payload=payload,
        idempotency_key=IdempotencyKey("sha256:" + sha256(key.encode()).hexdigest()),
        payload_digest=PayloadDigest("sha256:" + sha256(encoded.encode()).hexdigest()),
    )


def _append[PayloadT: BaseModel](
    connection: sqlite3.Connection,
    envelope: EventEnvelope[PayloadT],
    sequence: int,
) -> None:
    raw = inspect_raw_json(envelope.model_dump_json().encode())
    if not isinstance(raw, SafeDocument):
        raise RuntimeAuthorityError(code="BOOTSTRAP_EVENT_REJECTED")
    event = parse_collected_event(raw.value)
    payload = parse_event_payload(event)
    encoded = canonical_payload_json(payload)
    if event.payload_digest != "sha256:" + sha256(encoded.encode()).hexdigest():
        raise RuntimeAuthorityError(code="BOOTSTRAP_EVENT_DIGEST_MISMATCH")
    _ = connection.execute(
        """INSERT INTO ticket_events(
        event_id,idempotency_key,payload_digest,event_type,schema_version,occurred_at,received_at,
        actor_type,origin,authority,project_observation_id,project_id,project_resolution_state,
        repo_key,session_id,turn_id,ticket_id,work_item_id,causation_event_id,
        depends_on_event_ids_json,payload_json,ingest_seq)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event.event_id,
            event.idempotency_key,
            event.payload_digest,
            event.event_type.value,
            event.schema_version,
            event.occurred_at.isoformat(),
            None,
            event.actor_type.value,
            event.origin.value,
            payload.authority.value,
            event.project_observation_id,
            event.project_id,
            event.project_resolution_state.value,
            event.repo_key,
            event.session_id,
            None,
            None,
            None,
            event.causation_event_id,
            json.dumps(event.depends_on_event_ids),
            encoded,
            sequence,
        ),
    )
    _ = connection.execute(
        """INSERT INTO ingest_receipts(idempotency_key,event_id,payload_digest,state,ingest_seq)
        VALUES (?,?,?,'APPLIED',?)""",
        (event.idempotency_key, event.event_id, event.payload_digest, sequence),
    )


def bootstrap_runtime(database: Database, authority: VerifiedRuntimeAuthority) -> None:
    """Commit both canonical collector events and projections once, preserving existing history."""
    entry = authority.declaration
    policy = authority.policy
    repo_key = authority.resolution.repo_key
    if repo_key is None:
        raise RuntimeAuthorityError(code="REPO_IDENTITY_REQUIRED")
    root_key = authority.resolution.canonical_cwd
    if root_key is None:
        raise RuntimeAuthorityError(code="PROJECT_ROOT_INVALID")
    project = ProjectPayload(
        authority=StatusAuthority.SYSTEM_DERIVED,
        label=authority.project_label,
        logical_root_key=root_key,
        repo_key=repo_key,
        identity_source_hash=authority.registry.snapshot.digest,
    )
    identity = _envelope(authority, EventType.PROJECT_IDENTITY_RESOLVED, project)
    resolved = _envelope(
        authority,
        EventType.PROJECT_POLICY_RESOLVED,
        ReviewSignalPayload(
            authority=StatusAuthority.SYSTEM_DERIVED,
            reason_code="PROJECT_POLICY_RESOLVED",
            evidence_refs=(identity.event_id,),
        ),
        identity.event_id,
    )
    expected_project = (project.label, root_key, repo_key, "REGISTRY", project.identity_source_hash)
    expected_policy = (
        policy.wiki_requirement.value,
        policy.git_requirement.value,
        policy.authority_ceiling.value,
        policy.source_ref,
        policy.source_sha256,
        policy.snapshot_id,
    )
    with database.transaction() as connection:
        current_project = _PROJECT.validate_python(
            connection.execute(
                """SELECT label,logical_root_key,repo_key,identity_source,
                identity_source_hash,version
                FROM projects WHERE id=?""",
                (entry.project_id,),
            ).fetchone()
        )
        current_policy = _POLICY.validate_python(
            connection.execute(
                """SELECT wiki_authority,git_authority,authority_ceiling,evidence_ref,evidence_hash,
                policy_snapshot_id FROM project_policies WHERE project_id=?""",
                (entry.project_id,),
            ).fetchone()
        )
        upgrade = entry.registration_upgrade
        changing_registration = (
            current_project is not None and current_project[:5] != expected_project
        )
        if changing_registration and (
            upgrade is None
            or current_project is None
            or current_project[:4] != expected_project[:4]
            or current_project[4] != upgrade.previous_identity_source_hash
            or current_project[5] != upgrade.previous_project_version
            or current_policy is not None
        ):
            raise RuntimeAuthorityError(code="BOOTSTRAP_REGISTRATION_UPGRADE_REJECTED")
        if current_policy is not None and current_policy != expected_policy:
            raise RuntimeAuthorityError(code="BOOTSTRAP_EXISTING_STATE_MISMATCH")
        count = _COUNT.validate_python(
            connection.execute(
                "SELECT COUNT(*) FROM ticket_events WHERE event_id IN (?,?)",
                (identity.event_id, resolved.event_id),
            ).fetchone()
        )[0]
        if count:
            if count != _BOOTSTRAP_EVENT_COUNT or current_project is None or current_policy is None:
                raise RuntimeAuthorityError(code="BOOTSTRAP_STATE_INCOMPLETE")
            return
        if upgrade is not None and not changing_registration:
            raise RuntimeAuthorityError(code="BOOTSTRAP_REGISTRATION_UPGRADE_REJECTED")
        sequence = next_ingest_sequence(connection)
        if current_project is None or changing_registration:
            database.write_projection(
                connection,
                ProjectionWrite(
                    sequence,
                    identity.occurred_at,
                    ProjectChange(
                        project_id=entry.project_id,
                        label=project.label,
                        logical_root_key=root_key,
                        repo_key=repo_key,
                        identity_source="REGISTRY",
                        identity_source_hash=project.identity_source_hash,
                    ),
                ),
            )
        _append(connection, identity, sequence)
        if current_policy is None:
            _ = connection.execute(
                "INSERT INTO project_policies VALUES (?,?,?,?,?,?,?,?)",
                (entry.project_id, *expected_policy, resolved.occurred_at.isoformat()),
            )
        _append(connection, resolved, next_ingest_sequence(connection))
