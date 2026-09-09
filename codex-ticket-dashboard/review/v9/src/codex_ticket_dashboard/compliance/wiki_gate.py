"""Pure read-only Wiki compliance evaluation."""

from dataclasses import dataclass
from enum import StrEnum, unique
from pathlib import PurePosixPath
from typing import assert_never

from codex_ticket_dashboard.compliance.policy_resolver import (
    ComplianceCode,
    PolicyBlocked,
    PolicyResolution,
    ProjectPolicy,
    WikiRequirement,
)


@unique
class WikiGateStatus(StrEnum):
    """Wiki gate display states from the design contract."""

    SATISFIED = "SATISFIED"
    UPDATE_PENDING = "UPDATE-PENDING"
    BLOCKED = "BLOCKED"
    UNVERIFIED = "UNVERIFIED"
    COMPLIANCE_INCOMPLETE = "COMPLIANCE_INCOMPLETE"
    NOT_APPLICABLE = "N/A"


@dataclass(frozen=True, slots=True)
class WikiFileEvidence:
    """Hash-only evidence for one relative Markdown path."""

    relative_path: PurePosixPath
    sha256_before: str
    sha256_after: str


@dataclass(frozen=True, slots=True)
class WikiEvidence:
    """Observed Wiki facts with no file-writing capability."""

    files: tuple[WikiFileEvidence, ...]
    section_markers: tuple[str, ...]
    required_fields_present: bool
    strict_utf8_ok: bool
    generated_projection_target: bool

    @classmethod
    def empty(cls) -> "WikiEvidence":
        """Create an evidence-free read result."""
        return cls(
            files=(),
            section_markers=(),
            required_fields_present=False,
            strict_utf8_ok=False,
            generated_projection_target=False,
        )


@dataclass(frozen=True, slots=True)
class WikiGateAssessment:
    """Machine-readable Wiki verdict with an explicit no-write surface."""

    status: WikiGateStatus
    codes: tuple[ComplianceCode, ...]
    write_paths: tuple[PurePosixPath, ...] = ()


def evaluate_wiki_gate(
    policy: PolicyResolution,
    declared_requirement: WikiRequirement,
    evidence: WikiEvidence,
) -> WikiGateAssessment:
    """Compare a Wiki claim to verified policy and hash-only evidence."""
    match policy:
        case PolicyBlocked(code=code):
            return WikiGateAssessment(
                WikiGateStatus.COMPLIANCE_INCOMPLETE,
                (code, ComplianceCode.COMPLIANCE_INCOMPLETE),
            )
        case ProjectPolicy() as resolved:
            mismatch = (
                (ComplianceCode.POLICY_MISMATCH,)
                if declared_requirement is not resolved.wiki_requirement
                else ()
            )
            if mismatch:
                return WikiGateAssessment(
                    WikiGateStatus.COMPLIANCE_INCOMPLETE,
                    (*mismatch, ComplianceCode.COMPLIANCE_INCOMPLETE),
                )
            if evidence.generated_projection_target:
                return WikiGateAssessment(
                    WikiGateStatus.BLOCKED,
                    (
                        *mismatch,
                        ComplianceCode.GENERATED_PROJECTION_WRITE_FORBIDDEN,
                        ComplianceCode.COMPLIANCE_INCOMPLETE,
                    ),
                )
            return WikiGateAssessment(_wiki_status(resolved.wiki_requirement, evidence), mismatch)
        case unreachable:
            assert_never(unreachable)


def _wiki_status(requirement: WikiRequirement, evidence: WikiEvidence) -> WikiGateStatus:
    match requirement:
        case WikiRequirement.NOT_APPLICABLE:
            status = WikiGateStatus.NOT_APPLICABLE
        case WikiRequirement.CENTRAL_WIKI | WikiRequirement.PROJECT_LOCAL_WIKI:
            if not evidence.files:
                status = WikiGateStatus.UPDATE_PENDING
            elif (
                any(
                    path.relative_path.is_absolute()
                    or ".." in path.relative_path.parts
                    or path.relative_path.suffix.casefold() != ".md"
                    for path in evidence.files
                )
                or not evidence.section_markers
                or (not evidence.required_fields_present or not evidence.strict_utf8_ok)
            ):
                status = WikiGateStatus.UNVERIFIED
            elif all(path.sha256_before == path.sha256_after for path in evidence.files):
                status = WikiGateStatus.UPDATE_PENDING
            else:
                status = WikiGateStatus.SATISFIED
        case unreachable:
            assert_never(unreachable)
    return status
