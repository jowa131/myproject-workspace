"""Read-only bootstrap compatibility decisions shared by startup and preflight."""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum, unique
from hashlib import sha256
from typing import Final
from uuid import UUID

from pydantic import TypeAdapter

from codex_ticket_dashboard.compliance.runtime_authority import VerifiedRuntimeAuthority
from codex_ticket_dashboard.compliance.runtime_authority_models import (
    RuntimeAuthorityError,
    TaskAuthority,
)
from codex_ticket_dashboard.domain.events import EventType
from codex_ticket_dashboard.domain.identifiers import EventId

type ProjectIdentityState = tuple[str, str, str, str, str]
type ProjectState = tuple[str, str, str, str, str, int]
type PolicyState = tuple[str, str, str, str, str, str]

_PROJECT: Final[TypeAdapter[ProjectState | None]] = TypeAdapter(ProjectState | None)
_POLICY: Final[TypeAdapter[PolicyState | None]] = TypeAdapter(PolicyState | None)
_COUNT: Final = TypeAdapter(tuple[int])
_BOOTSTRAP_EVENT_COUNT: Final = 2


@unique
class RuntimeBootstrapAction(StrEnum):
    """Mutations startup may perform after an exact read-only state decision."""

    UNCHANGED = "UNCHANGED"
    INITIALIZE = "INITIALIZE"
    REGISTRATION_UPGRADE = "REGISTRATION_UPGRADE"
    POLICY_EVIDENCE_RENEWAL = "POLICY_EVIDENCE_RENEWAL"


@dataclass(frozen=True, slots=True)
class RuntimeBootstrapDecision:
    """A transaction-local bootstrap action with its expected canonical state."""

    action: RuntimeBootstrapAction
    expected_project: ProjectIdentityState
    expected_policy: PolicyState
    write_project: bool
    insert_policy: bool


@dataclass(frozen=True, slots=True)
class _BootstrapState:
    current_project: ProjectState | None
    current_policy: PolicyState | None
    expected_project: ProjectIdentityState
    expected_policy: PolicyState
    event_count: int


def bootstrap_event_id(declaration_sha256: str, kind: EventType) -> EventId:
    """Derive the canonical event identifier for one pinned declaration and event kind."""
    key = declaration_sha256 + ":" + kind.value
    return EventId("evt_" + str(UUID(bytes=sha256(key.encode()).digest()[:16], version=4)))


def evaluate_runtime_bootstrap_state(
    connection: sqlite3.Connection,
    authority: VerifiedRuntimeAuthority,
) -> RuntimeBootstrapDecision:
    """Decide bootstrap compatibility using queries only; the caller owns the transaction."""
    entry = authority.declaration
    repo_key = authority.resolution.repo_key
    root_key = authority.resolution.canonical_cwd
    if repo_key is None:
        raise RuntimeAuthorityError(code="REPO_IDENTITY_REQUIRED")
    if root_key is None:
        raise RuntimeAuthorityError(code="PROJECT_ROOT_INVALID")
    expected_project: ProjectIdentityState = (
        authority.project_label,
        root_key,
        repo_key,
        "REGISTRY",
        authority.registry.snapshot.digest,
    )
    policy = authority.policy
    expected_policy: PolicyState = (
        policy.wiki_requirement.value,
        policy.git_requirement.value,
        policy.authority_ceiling.value,
        policy.source_ref,
        policy.source_sha256,
        policy.snapshot_id,
    )
    current_project = _PROJECT.validate_python(
        connection.execute(
            """SELECT label,logical_root_key,repo_key,identity_source,identity_source_hash,version
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
    event_count = _COUNT.validate_python(
        connection.execute(
            "SELECT COUNT(*) FROM ticket_events WHERE event_id IN (?,?)",
            (
                bootstrap_event_id(
                    authority.declaration_sha256,
                    EventType.PROJECT_IDENTITY_RESOLVED,
                ),
                bootstrap_event_id(authority.declaration_sha256, EventType.PROJECT_POLICY_RESOLVED),
            ),
        ).fetchone()
    )[0]
    changing_registration = (
        current_project is not None and current_project[:5] != expected_project
    )
    _validate_renewal_identity(entry, current_project, expected_project)
    renewal = entry.policy_evidence_renewal
    upgrade = entry.registration_upgrade
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
        return _policy_renewal_decision(
            connection,
            authority,
            _BootstrapState(
                current_project,
                current_policy,
                expected_project,
                expected_policy,
                event_count,
            ),
        )
    if renewal is not None:
        if current_policy == expected_policy and event_count == _BOOTSTRAP_EVENT_COUNT:
            return RuntimeBootstrapDecision(
                RuntimeBootstrapAction.UNCHANGED,
                expected_project,
                expected_policy,
                write_project=False,
                insert_policy=False,
            )
        code = (
            "BOOTSTRAP_POLICY_RENEWAL_PREVIOUS_MISMATCH"
            if current_policy is None
            else "BOOTSTRAP_STATE_INCOMPLETE"
        )
        raise RuntimeAuthorityError(code=code)
    if event_count:
        if (
            event_count != _BOOTSTRAP_EVENT_COUNT
            or current_project is None
            or current_policy is None
        ):
            raise RuntimeAuthorityError(code="BOOTSTRAP_STATE_INCOMPLETE")
        return RuntimeBootstrapDecision(
            RuntimeBootstrapAction.UNCHANGED,
            expected_project,
            expected_policy,
            write_project=False,
            insert_policy=False,
        )
    if upgrade is not None and not changing_registration:
        raise RuntimeAuthorityError(code="BOOTSTRAP_REGISTRATION_UPGRADE_REJECTED")
    action = (
        RuntimeBootstrapAction.REGISTRATION_UPGRADE
        if changing_registration
        else RuntimeBootstrapAction.INITIALIZE
    )
    return RuntimeBootstrapDecision(
        action,
        expected_project,
        expected_policy,
        write_project=current_project is None or changing_registration,
        insert_policy=current_policy is None,
    )


def _validate_renewal_identity(
    declaration: TaskAuthority,
    current_project: ProjectState | None,
    expected_project: ProjectIdentityState,
) -> None:
    if declaration.policy_evidence_renewal is None:
        return
    if (
        current_project is None
        or current_project[:5] != expected_project
        or declaration.registration_upgrade is not None
    ):
        raise RuntimeAuthorityError(code="BOOTSTRAP_POLICY_RENEWAL_IDENTITY_MISMATCH")


def _policy_renewal_decision(
    connection: sqlite3.Connection,
    authority: VerifiedRuntimeAuthority,
    state: _BootstrapState,
) -> RuntimeBootstrapDecision:
    renewal = authority.declaration.policy_evidence_renewal
    if renewal is None:
        raise RuntimeAuthorityError(code="BOOTSTRAP_EXISTING_STATE_MISMATCH")
    current_project = state.current_project
    current_policy = state.current_policy
    if current_policy is None:
        raise RuntimeAuthorityError(code="BOOTSTRAP_POLICY_RENEWAL_PREVIOUS_MISMATCH")
    if current_project is None or current_project[:5] != state.expected_project:
        raise RuntimeAuthorityError(code="BOOTSTRAP_POLICY_RENEWAL_IDENTITY_MISMATCH")
    if current_policy[:3] != state.expected_policy[:3]:
        raise RuntimeAuthorityError(code="BOOTSTRAP_POLICY_RENEWAL_PERMISSION_CHANGE")
    if (
        current_policy[4] != renewal.previous_evidence_hash
        or current_policy[5] != renewal.previous_policy_snapshot_id
    ):
        raise RuntimeAuthorityError(code="BOOTSTRAP_POLICY_RENEWAL_PREVIOUS_MISMATCH")
    if state.event_count:
        raise RuntimeAuthorityError(code="BOOTSTRAP_STATE_INCOMPLETE")
    active_review_count = _COUNT.validate_python(
        connection.execute(
            "SELECT COUNT(*) FROM tickets WHERE project_id=? AND status='IN_REVIEW'",
            (authority.declaration.project_id,),
        ).fetchone()
    )[0]
    if active_review_count:
        raise RuntimeAuthorityError(code="BOOTSTRAP_POLICY_RENEWAL_REVIEW_ACTIVE")
    return RuntimeBootstrapDecision(
        RuntimeBootstrapAction.POLICY_EVIDENCE_RENEWAL,
        state.expected_project,
        state.expected_policy,
        write_project=False,
        insert_policy=False,
    )
