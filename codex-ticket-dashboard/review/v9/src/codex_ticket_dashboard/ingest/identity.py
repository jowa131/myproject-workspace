"""Exact bootstrap admission for pending project identity."""

from dataclasses import dataclass
from enum import StrEnum, unique

from codex_ticket_dashboard.compliance.project_registry import RegistrySnapshot
from codex_ticket_dashboard.domain.identifiers import ProjectId, ProjectObservationId


@unique
class PendingIdentityState(StrEnum):
    """Lifecycle state of a project observation awaiting identity."""

    PENDING_IDENTITY = "PENDING_IDENTITY"
    RESOLVED = "RESOLVED"


@unique
class ResolutionDependencyKind(StrEnum):
    """Permitted and forbidden bootstrap dependency shapes."""

    EXACT_PENDING_OBSERVATION = "EXACT_PENDING_OBSERVATION"
    GENERIC_PENDING_IDENTITY = "GENERIC_PENDING_IDENTITY"


@unique
class BootstrapCode(StrEnum):
    """Stable bootstrap admission outcomes."""

    APPLIED = "APPLIED"
    PROJECT_IDENTITY_RESOLUTION_REJECTED = "PROJECT_IDENTITY_RESOLUTION_REJECTED"


@dataclass(frozen=True, slots=True)
class PendingIdentity:
    """One persisted identity observation state."""

    observation_id: ProjectObservationId
    state: PendingIdentityState
    canonical_cwd: str


@dataclass(frozen=True, slots=True)
class IdentityResolutionClaim:
    """Digest-bound claim to resolve exactly one pending observation."""

    observation_id: ProjectObservationId
    resolved_project_id: ProjectId
    resolution_source_ref: str
    resolution_source_sha256: str
    dependency_kind: ResolutionDependencyKind


@dataclass(frozen=True, slots=True)
class IdentityMapping:
    """Accepted observation-to-project mapping."""

    observation_id: ProjectObservationId
    project_id: ProjectId


@dataclass(frozen=True, slots=True)
class BootstrapResolution:
    """Atomic mapping and targeted replay intent."""

    code: BootstrapCode
    mapping: IdentityMapping | None
    replay_observation_ids: tuple[ProjectObservationId, ...]


def resolve_pending_identity(
    pending: tuple[PendingIdentity, ...],
    snapshot: RegistrySnapshot,
    claim: IdentityResolutionClaim,
) -> BootstrapResolution:
    """Accept only an exact pending observation and current registry digest."""
    matching = tuple(item for item in pending if item.observation_id == claim.observation_id)
    matched_project_id = (
        snapshot.unique_project_for(matching[0].canonical_cwd) if len(matching) == 1 else None
    )
    accepted = (
        len(matching) == 1
        and matching[0].state is PendingIdentityState.PENDING_IDENTITY
        and claim.resolved_project_id == matched_project_id
        and claim.resolution_source_ref == snapshot.snapshot_id
        and claim.resolution_source_sha256 == snapshot.digest
        and claim.dependency_kind is ResolutionDependencyKind.EXACT_PENDING_OBSERVATION
    )
    if not accepted:
        return BootstrapResolution(
            BootstrapCode.PROJECT_IDENTITY_RESOLUTION_REJECTED,
            None,
            (),
        )
    return BootstrapResolution(
        BootstrapCode.APPLIED,
        IdentityMapping(claim.observation_id, claim.resolved_project_id),
        (claim.observation_id,),
    )
