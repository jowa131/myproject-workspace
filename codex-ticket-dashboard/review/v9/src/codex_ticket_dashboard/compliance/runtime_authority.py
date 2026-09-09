"""Read actual pinned sources and resolve one explicit runtime policy before storage mutation."""

import msvcrt
import os
import subprocess
import tomllib
from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from codex_ticket_dashboard.compliance.policy_resolver import (
    GitRequirement,
    PolicyBlocked,
    PolicyRequest,
    ProjectPolicy,
    SourceEvidence,
    resolve_project_policy,
)
from codex_ticket_dashboard.compliance.project_registry import (
    DefaultWindowsPathCanonicalizer,
    ProjectObservation,
    ProjectRegistry,
    ProjectResolution,
)
from codex_ticket_dashboard.compliance.runtime_authority_models import (
    AuthorizingProvenance,
    FilePin,
    RegistrationRecord,
    RuntimeAuthorityError,
    TaskAuthority,
)
from codex_ticket_dashboard.config import ConfigLoadError, DashboardConfig
from codex_ticket_dashboard.domain.events import ProjectResolutionState
from codex_ticket_dashboard.domain.identifiers import new_project_observation_id
from codex_ticket_dashboard.storage.path_security import parse_local_fixed_path
from codex_ticket_dashboard.storage.win32_handles import verify_handle
from codex_ticket_dashboard.storage.win32_native import WinHandle


@dataclass(frozen=True, slots=True)
class VerifiedRuntimeAuthority:
    """Validated inputs needed by the single collector bootstrap transaction."""

    declaration: TaskAuthority
    declaration_sha256: str
    registry: ProjectRegistry
    resolution: ProjectResolution
    policy: ProjectPolicy
    project_label: str


def read_pinned_source(pin: FilePin) -> bytes:
    """Read through a final-path-verified handle without changing source ACLs."""
    try:
        path = parse_local_fixed_path(pin.path)
        canonical = DefaultWindowsPathCanonicalizer().canonicalize(path)
        if canonical.contains_reparse:
            raise RuntimeAuthorityError(code="SOURCE_REPARSE_FORBIDDEN")
        with path.open("rb") as source:
            _ = verify_handle(WinHandle(msvcrt.get_osfhandle(source.fileno())), path)
            content = source.read()
    except OSError:
        raise RuntimeAuthorityError(code="SOURCE_UNAVAILABLE") from None
    if sha256(content).hexdigest() != pin.sha256:
        raise RuntimeAuthorityError(code="SOURCE_DRIFT")
    return content


def _repository_identity(
    declaration: TaskAuthority,
    config: DashboardConfig,
) -> tuple[ProjectRegistry, ProjectResolution]:
    _ = read_pinned_source(declaration.git_executable)
    root = parse_local_fixed_path(declaration.root)
    canonicalizer = DefaultWindowsPathCanonicalizer()
    if not root.is_dir() or canonicalizer.canonicalize(root).contains_reparse:
        raise RuntimeAuthorityError(code="PROJECT_ROOT_INVALID")
    try:
        observed = subprocess.run(  # noqa: S603 -- digest-pinned executable, read-only fixed command.
            [
                str(declaration.git_executable.path),
                "-C",
                str(root),
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
            env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeAuthorityError(code="REPO_IDENTITY_UNAVAILABLE") from None
    if observed.returncode != 0:
        raise RuntimeAuthorityError(code="REPO_IDENTITY_UNAVAILABLE")
    common_dir = Path(observed.stdout.strip())
    if common_dir != declaration.git_common_dir or not common_dir.is_dir():
        raise RuntimeAuthorityError(code="REPO_IDENTITY_MISMATCH")
    registry = ProjectRegistry(config.projects, canonicalizer)
    resolution = registry.resolve(
        ProjectObservation(new_project_observation_id(), root, common_dir)
    )
    if resolution.state is not ProjectResolutionState.RESOLVED or resolution.repo_key is None:
        raise RuntimeAuthorityError(code="REPO_IDENTITY_MISMATCH")
    return registry, resolution


def verify_runtime_authority(
    config: DashboardConfig,
    config_path: Path,
    authority_path: Path,
    expected_sha256: str,
) -> VerifiedRuntimeAuthority:
    """Resolve pinned registration, current policy, task provenance, and repository identity."""
    try:
        pin = FilePin(path=authority_path, reference=authority_path.name, sha256=expected_sha256)
        declaration = TaskAuthority.model_validate_json(read_pinned_source(pin))
        config_bytes = read_pinned_source(
            FilePin(
                path=config_path,
                reference=config_path.name,
                sha256=declaration.config_sha256,
            )
        )
        verified_config = DashboardConfig.model_validate(
            tomllib.loads(config_bytes.decode("utf-8"))
        )
        if verified_config != config:
            raise RuntimeAuthorityError(code="CONFIG_SOURCE_MISMATCH")
        registration = RegistrationRecord.model_validate_json(
            read_pinned_source(declaration.registration)
        )
        provenance = AuthorizingProvenance.model_validate_json(
            read_pinned_source(declaration.provenance)
        )
    except (ValidationError, ConfigLoadError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        raise RuntimeAuthorityError(code="AUTHORITY_DECLARATION_INVALID") from None
    if len(config.projects) != 1:
        raise RuntimeAuthorityError(code="REGISTRY_SCOPE_MISMATCH")
    entry = config.projects[0]
    if (
        entry.project_id != declaration.project_id
        or entry.roots != (declaration.root,)
        or entry.worktree_roots != ()
        or entry.wiki_authority.value != declaration.wiki_authority
        or entry.authority_source_ref != declaration.registration.reference
        or entry.authority_source_sha256 != declaration.registration.sha256
        or registration.project_id != entry.project_id
        or registration.label != entry.label
        or registration.roots != entry.roots
        or registration.worktree_roots != entry.worktree_roots
        or registration.wiki_authority != declaration.wiki_authority
    ):
        raise RuntimeAuthorityError(code="REGISTRY_SOURCE_MISMATCH")
    if (
        provenance.authorizing_session_id != declaration.authorizing_session_id
        or declaration.authorizing_session_id != f"thr_{provenance.thread_id}"
        or provenance.cwd != declaration.root
    ):
        raise RuntimeAuthorityError(code="AUTHORIZING_PROVENANCE_MISMATCH")
    if {source.role for source in declaration.policy_sources} != {"global", "project"} or len(
        {source.path for source in declaration.policy_sources}
    ) != len(declaration.policy_sources):
        raise RuntimeAuthorityError(code="POLICY_SOURCES_REQUIRED")
    for source in declaration.policy_sources:
        _ = read_pinned_source(source)
    registry, resolution = _repository_identity(declaration, config)
    policy = resolve_project_policy(
        PolicyRequest(
            entry,
            GitRequirement.STATUS_ONLY,
            GitRequirement.STATUS_ONLY,
            SourceEvidence(
                reference=entry.authority_source_ref,
                sha256=entry.authority_source_sha256,
                project_local_migration_accepted=False,
            ),
        )
    )
    if isinstance(policy, PolicyBlocked):
        raise RuntimeAuthorityError(policy.code.value)
    effective_digest = sha256((registry.snapshot.digest + expected_sha256).encode()).hexdigest()
    effective_policy = replace(
        policy,
        source_ref=authority_path.name,
        source_sha256=expected_sha256,
        snapshot_id="pol_" + effective_digest[:24],
        snapshot_digest="sha256:" + effective_digest,
    )
    return VerifiedRuntimeAuthority(
        declaration,
        expected_sha256,
        registry,
        resolution,
        effective_policy,
        entry.label,
    )
