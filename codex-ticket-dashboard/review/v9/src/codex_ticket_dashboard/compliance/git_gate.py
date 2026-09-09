"""Pure read-only Git compliance evaluation."""

from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import PurePosixPath
from typing import Final, assert_never

from codex_ticket_dashboard.compliance.policy_resolver import (
    ComplianceCode,
    GitRequirement,
    PolicyBlocked,
    PolicyResolution,
    ProjectPolicy,
)

_REQUIREMENT_RANK: Final = {
    GitRequirement.NOT_APPLICABLE: 0,
    GitRequirement.STATUS_ONLY: 1,
    GitRequirement.COMMIT: 2,
    GitRequirement.PUSH: 3,
}


@unique
class GitGateStatus(StrEnum):
    """Git gate display states from the design contract."""

    SATISFIED = "SATISFIED"
    STATUS_ONLY = "STATUS-ONLY"
    COMMIT_PENDING = "COMMIT-PENDING"
    PUSH_PENDING = "PUSH-PENDING"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"
    NOT_APPLICABLE = "N/A"


@dataclass(frozen=True, slots=True)
class GitEvidence:
    """Already-observed Git facts; contains no command execution capability."""

    status_observed: bool
    changed_paths: tuple[PurePosixPath, ...]
    commit_sha: str | None
    commit_paths: tuple[PurePosixPath, ...]
    pushed_revision: str | None
    remote_revision: str | None

    @classmethod
    def empty(cls) -> "GitEvidence":
        """Create an evidence-free read result."""
        return cls(
            status_observed=False,
            changed_paths=(),
            commit_sha=None,
            commit_paths=(),
            pushed_revision=None,
            remote_revision=None,
        )


@dataclass(frozen=True, slots=True)
class GitGateAssessment:
    """Machine-readable Git verdict with an explicit no-mutation surface."""

    status: GitGateStatus
    codes: tuple[ComplianceCode, ...]
    mutation_commands: tuple[str, ...] = ()


def evaluate_git_gate(
    policy: PolicyResolution,
    declared_requirement: GitRequirement,
    evidence: GitEvidence,
) -> GitGateAssessment:
    """Compare a claim to verified policy and observed Git facts."""
    match policy:
        case PolicyBlocked(code=code):
            return GitGateAssessment(
                GitGateStatus.BLOCKED,
                (code, ComplianceCode.COMPLIANCE_INCOMPLETE),
            )
        case ProjectPolicy() as resolved:
            codes = (
                (ComplianceCode.POLICY_MISMATCH,)
                if declared_requirement is not resolved.git_requirement
                else ()
            )
            if (
                _REQUIREMENT_RANK[resolved.git_requirement]
                > _REQUIREMENT_RANK[resolved.authority_ceiling]
            ):
                return GitGateAssessment(
                    GitGateStatus.BLOCKED,
                    (
                        *codes,
                        ComplianceCode.AUTHORITY_CEILING_EXCEEDED,
                        ComplianceCode.COMPLIANCE_INCOMPLETE,
                    ),
                )
            status = _git_status(resolved.git_requirement, evidence)
            if codes and status in {
                GitGateStatus.SATISFIED,
                GitGateStatus.STATUS_ONLY,
                GitGateStatus.NOT_APPLICABLE,
            }:
                return GitGateAssessment(
                    GitGateStatus.BLOCKED,
                    (*codes, ComplianceCode.COMPLIANCE_INCOMPLETE),
                )
            return GitGateAssessment(status, codes)
        case unreachable:
            assert_never(unreachable)


def _git_status(requirement: GitRequirement, evidence: GitEvidence) -> GitGateStatus:
    match requirement:
        case GitRequirement.NOT_APPLICABLE:
            status = GitGateStatus.NOT_APPLICABLE
        case GitRequirement.STATUS_ONLY:
            status = (
                GitGateStatus.STATUS_ONLY if evidence.status_observed else GitGateStatus.UNVERIFIED
            )
        case GitRequirement.COMMIT:
            if evidence.commit_sha is None:
                status = GitGateStatus.COMMIT_PENDING
            elif set(evidence.changed_paths) != set(evidence.commit_paths):
                status = GitGateStatus.UNVERIFIED
            else:
                status = GitGateStatus.SATISFIED
        case GitRequirement.PUSH:
            if evidence.commit_sha is None:
                status = GitGateStatus.COMMIT_PENDING
            elif (
                evidence.pushed_revision is None
                or evidence.remote_revision is None
                or evidence.pushed_revision != evidence.remote_revision
            ):
                status = GitGateStatus.PUSH_PENDING
            else:
                status = GitGateStatus.SATISFIED
        case unreachable:
            assert_never(unreachable)
    return status
