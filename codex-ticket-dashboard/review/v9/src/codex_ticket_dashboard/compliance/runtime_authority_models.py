"""Closed externally pinned declarations; none of these fields discover or grant authority."""

from pathlib import Path
from typing import Annotated, ClassVar, Literal, final

from pydantic import BaseModel, ConfigDict, Field, field_validator

from codex_ticket_dashboard.domain.events import ValidatedProjectId, ValidatedSessionId

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Reference = Annotated[str, Field(min_length=1, max_length=240)]
PolicySnapshotId = Annotated[str, Field(pattern=r"^pol_[0-9a-f]{24}$")]


@final
class RuntimeAuthorityError(ValueError):
    """Report only a named failure, without source contents or rejected paths."""

    def __init__(self, code: str) -> None:
        """Keep provenance and source bytes out of exceptions."""
        super().__init__(code)
        self.code: str = code


class ClosedModel(BaseModel):
    """Untrusted declarations are frozen and reject unknown fields."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True,
        extra="forbid",
        hide_input_in_errors=True,
    )


class FilePin(ClosedModel):
    """Explicit file location, evidence reference, and expected actual-byte digest."""

    path: Path
    reference: Reference
    sha256: Digest

    @field_validator("path")
    @classmethod
    def absolute_path(cls, value: Path) -> Path:
        """Reject relative source locations before opening them."""
        if not value.is_absolute():
            raise RuntimeAuthorityError(code="SOURCE_PATH_INVALID")
        return value


class PolicySource(FilePin):
    """Keep global and project policy evidence separate from registration identity."""

    role: Literal["global", "project"]


class RegistrationUpgrade(ClosedModel):
    """Pin the previous registration version without granting new project or policy rights."""

    previous_identity_source_hash: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    previous_project_version: int = Field(gt=0)


class PolicyEvidenceRenewal(ClosedModel):
    """Pin the exact existing policy row approved for evidence-only renewal."""

    previous_evidence_hash: Digest
    previous_policy_snapshot_id: PolicySnapshotId


class TaskAuthority(ClosedModel):
    """One approved current-project scope with no mutation authority above status observation."""

    schema_version: Literal[1]
    project_id: ValidatedProjectId
    root: Path
    worktree_roots: tuple[()] = ()
    config_sha256: Digest
    registration: FilePin
    policy_sources: tuple[PolicySource, PolicySource]
    git_requirement: Literal["STATUS_ONLY"]
    authority_ceiling: Literal["STATUS_ONLY"]
    wiki_authority: Literal["CENTRAL_WIKI"]
    git_executable: FilePin
    git_common_dir: Path
    authorizing_session_id: ValidatedSessionId
    provenance: FilePin
    registration_upgrade: RegistrationUpgrade | None = None
    policy_evidence_renewal: PolicyEvidenceRenewal | None = None


class RegistrationRecord(BaseModel):
    """Validate registration identity fields without interpreting descriptive prose as authority."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    schema_version: Literal[1]
    record_kind: Literal["PROJECT_REGISTRATION_AUTHORITY"]
    project_id: ValidatedProjectId
    label: str
    roots: tuple[Path, ...]
    worktree_roots: tuple[Path, ...]
    wiki_authority: Literal["CENTRAL_WIKI"]


class AuthorizingProvenance(BaseModel):
    """Reference the explicit authorizing task without inventing runtime lifecycle observations."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    schema_version: Literal[1]
    thread_id: str
    authorizing_session_id: ValidatedSessionId
    cwd: Path
    thread_kind: Literal["codex"]
    raw_prompt_or_transcript_stored: Literal[False]
