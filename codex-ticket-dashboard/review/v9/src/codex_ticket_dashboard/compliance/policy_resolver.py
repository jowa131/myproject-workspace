"""Digest-bound read-only Git and Wiki policy resolution."""

import json
from dataclasses import dataclass
from enum import StrEnum, unique
from hashlib import sha256
from typing import assert_never

from codex_ticket_dashboard.config import ProjectRegistryEntry, WikiAuthority
from codex_ticket_dashboard.domain.identifiers import ProjectId


@unique
class GitRequirement(StrEnum):
    """Git evidence levels ordered separately by the gate."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    STATUS_ONLY = "STATUS_ONLY"
    COMMIT = "COMMIT"
    PUSH = "PUSH"


@unique
class WikiRequirement(StrEnum):
    """Approved Wiki authority destinations."""

    NOT_APPLICABLE = "NOT_APPLICABLE"
    CENTRAL_WIKI = "CENTRAL_WIKI"
    PROJECT_LOCAL_WIKI = "PROJECT_LOCAL_WIKI"


@unique
class ComplianceCode(StrEnum):
    """Stable machine-readable compliance outcomes."""

    POLICY_UNRESOLVED = "POLICY_UNRESOLVED"
    POLICY_DRIFT = "POLICY_DRIFT"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    AUTHORITY_CEILING_EXCEEDED = "AUTHORITY_CEILING_EXCEEDED"
    GENERATED_PROJECTION_WRITE_FORBIDDEN = "GENERATED_PROJECTION_WRITE_FORBIDDEN"
    COMPLIANCE_INCOMPLETE = "COMPLIANCE_INCOMPLETE"
    EVIDENCE_INCOMPLETE = "EVIDENCE_INCOMPLETE"


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Current read-only observation of one authority source."""

    reference: str
    sha256: str
    project_local_migration_accepted: bool


@dataclass(frozen=True, slots=True)
class PolicyRequest:
    """Inputs required to resolve a project policy snapshot."""

    entry: ProjectRegistryEntry
    git_requirement: GitRequirement
    authority_ceiling: GitRequirement
    source: SourceEvidence | None


@dataclass(frozen=True, slots=True)
class ProjectPolicy:
    """Verified immutable policy used by both compliance gates."""

    project_id: ProjectId
    git_requirement: GitRequirement
    authority_ceiling: GitRequirement
    wiki_requirement: WikiRequirement
    source_ref: str
    source_sha256: str
    snapshot_id: str
    snapshot_digest: str


@dataclass(frozen=True, slots=True)
class PolicyBlocked:
    """Named reason that policy could not be resolved safely."""

    code: ComplianceCode


type PolicyResolution = ProjectPolicy | PolicyBlocked


def resolve_project_policy(request: PolicyRequest) -> PolicyResolution:
    """Resolve registry policy only when its current source still matches."""
    source = request.source
    if source is None or source.reference != request.entry.authority_source_ref:
        return PolicyBlocked(ComplianceCode.POLICY_UNRESOLVED)
    if source.sha256 != request.entry.authority_source_sha256:
        return PolicyBlocked(ComplianceCode.POLICY_DRIFT)
    wiki_requirement = _wiki_requirement(request.entry.wiki_authority)
    if (
        wiki_requirement is WikiRequirement.PROJECT_LOCAL_WIKI
        and not source.project_local_migration_accepted
    ):
        return PolicyBlocked(ComplianceCode.POLICY_UNRESOLVED)
    encoded = json.dumps(
        {
            "authority_ceiling": request.authority_ceiling,
            "git_requirement": request.git_requirement,
            "project_id": request.entry.project_id,
            "source_ref": source.reference,
            "source_sha256": source.sha256,
            "wiki_requirement": wiki_requirement,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = "sha256:" + sha256(encoded).hexdigest()
    return ProjectPolicy(
        project_id=request.entry.project_id,
        git_requirement=request.git_requirement,
        authority_ceiling=request.authority_ceiling,
        wiki_requirement=wiki_requirement,
        source_ref=source.reference,
        source_sha256=source.sha256,
        snapshot_id="pol_" + digest.removeprefix("sha256:")[:24],
        snapshot_digest=digest,
    )


def _wiki_requirement(authority: WikiAuthority) -> WikiRequirement:
    match authority:
        case WikiAuthority.CENTRAL_WIKI:
            return WikiRequirement.CENTRAL_WIKI
        case WikiAuthority.PROJECT_LOCAL_WIKI:
            return WikiRequirement.PROJECT_LOCAL_WIKI
        case unreachable:
            assert_never(unreachable)
