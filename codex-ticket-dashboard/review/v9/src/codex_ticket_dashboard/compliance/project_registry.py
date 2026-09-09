"""Registry-only Windows project identity resolution."""

import base64
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PureWindowsPath
from typing import Final, Protocol, final

from codex_ticket_dashboard.config import ProjectRegistryEntry
from codex_ticket_dashboard.domain.events import ProjectResolutionState
from codex_ticket_dashboard.domain.identifiers import (
    ProjectId,
    ProjectObservationId,
    RepoKey,
)

_WINDOWS_DRIVE_ROOT_LENGTH: Final = 3


@dataclass(frozen=True, slots=True)
class CanonicalWindowsPath:
    """A display-safe canonical path plus comparison-only components."""

    display: str
    comparison_parts: tuple[str, ...]
    contains_reparse: bool


class WindowsPathCanonicalizer(Protocol):
    """Resolve a Windows path without granting mutation capability."""

    def canonicalize(self, path: Path) -> CanonicalWindowsPath:
        """Return the canonical display path and case-insensitive components."""
        ...


@dataclass(frozen=True, slots=True)
class DefaultWindowsPathCanonicalizer:
    """Canonicalize local paths while preserving their display casing."""

    def canonicalize(self, path: Path) -> CanonicalWindowsPath:
        """Resolve aliases and normalize Windows separators and drive casing."""
        resolved = path.resolve(strict=False)
        windows_path = PureWindowsPath(str(resolved))
        drive = windows_path.drive.upper()
        tail = windows_path.parts[1:] if windows_path.drive else windows_path.parts
        display = str(PureWindowsPath(drive + "\\", *tail)) if drive else str(windows_path)
        return CanonicalWindowsPath(
            display=(
                display.rstrip("\\") if len(display) > _WINDOWS_DRIVE_ROOT_LENGTH else display
            ),
            comparison_parts=tuple(part.casefold() for part in PureWindowsPath(display).parts),
            contains_reparse=_contains_reparse(path),
        )


@dataclass(frozen=True, slots=True)
class ProjectObservation:
    """One path observation before registry identity is known."""

    observation_id: ProjectObservationId
    cwd: Path
    git_common_dir: Path | None


@dataclass(frozen=True, slots=True)
class RegistryProjectSnapshot:
    """Identity fields retained from one registry entry."""

    project_id: ProjectId
    canonical_roots: tuple[str, ...]
    canonical_worktree_roots: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RegistrySnapshot:
    """Immutable digest-bound view of the approved registry."""

    snapshot_id: str
    digest: str
    projects: tuple[RegistryProjectSnapshot, ...]

    def unique_project_for(self, canonical_cwd: str) -> ProjectId | None:
        """Return the only registry project containing a canonical observation path."""
        windows_path = PureWindowsPath(canonical_cwd)
        if not windows_path.is_absolute():
            return None
        candidate = CanonicalWindowsPath(
            display=str(windows_path),
            comparison_parts=tuple(part.casefold() for part in windows_path.parts),
            contains_reparse=False,
        )
        matches = {
            project.project_id
            for project in self.projects
            if any(
                _contains(
                    CanonicalWindowsPath(
                        display=root,
                        comparison_parts=tuple(
                            part.casefold() for part in PureWindowsPath(root).parts
                        ),
                        contains_reparse=False,
                    ),
                    candidate,
                )
                for root in (*project.canonical_roots, *project.canonical_worktree_roots)
            )
        }
        return next(iter(matches)) if len(matches) == 1 else None


@dataclass(frozen=True, slots=True)
class ProjectResolution:
    """Fail-closed outcome for one observed working directory."""

    observation_id: ProjectObservationId
    state: ProjectResolutionState
    project_id: ProjectId | None
    repo_key: RepoKey | None
    canonical_cwd: str | None


@final
class ProjectRegistry:
    """Resolve observations only through user-approved registry entries."""

    def __init__(
        self,
        entries: tuple[ProjectRegistryEntry, ...],
        canonicalizer: WindowsPathCanonicalizer | None = None,
    ) -> None:
        """Build a deterministic in-memory snapshot without changing config."""
        self._canonicalizer = canonicalizer or DefaultWindowsPathCanonicalizer()
        self._canonical_entries = tuple(
            (
                entry,
                tuple(self._canonicalizer.canonicalize(root) for root in entry.roots),
                tuple(self._canonicalizer.canonicalize(root) for root in entry.worktree_roots),
            )
            for entry in entries
        )
        ordered_entries = tuple(
            sorted(self._canonical_entries, key=lambda item: item[0].project_id)
        )
        projects = tuple(
            RegistryProjectSnapshot(
                project_id=entry.project_id,
                canonical_roots=tuple(root.display for root in roots),
                canonical_worktree_roots=tuple(root.display for root in worktree_roots),
            )
            for entry, roots, worktree_roots in ordered_entries
        )
        encoded = json.dumps(
            [
                {
                    "authority_source_ref": entry.authority_source_ref,
                    "authority_source_sha256": entry.authority_source_sha256,
                    "label": entry.label,
                    "project_id": project.project_id,
                    "roots": project.canonical_roots,
                    "schema_version": entry.schema_version,
                    "wiki_authority": entry.wiki_authority,
                    "worktree_roots": project.canonical_worktree_roots,
                }
                for (entry, _, _), project in zip(ordered_entries, projects, strict=True)
            ],
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode()
        digest = "sha256:" + sha256(encoded).hexdigest()
        self.snapshot = RegistrySnapshot(
            snapshot_id="reg_" + digest.removeprefix("sha256:")[:24],
            digest=digest,
            projects=projects,
        )

    def resolve(self, observation: ProjectObservation) -> ProjectResolution:
        """Resolve exactly one registry entry or retain an unresolved state."""
        if not observation.cwd.is_absolute():
            return ProjectResolution(
                observation_id=observation.observation_id,
                state=ProjectResolutionState.UNCLASSIFIED,
                project_id=None,
                repo_key=None,
                canonical_cwd=None,
            )
        cwd = self._canonicalizer.canonicalize(observation.cwd)
        if cwd.contains_reparse:
            return ProjectResolution(
                observation_id=observation.observation_id,
                state=ProjectResolutionState.UNCLASSIFIED,
                project_id=None,
                repo_key=None,
                canonical_cwd=cwd.display,
            )
        matches = tuple(
            entry
            for entry, roots, worktree_roots in self._canonical_entries
            if any(
                not canonical_root.contains_reparse
                and _contains(canonical_root, cwd)
                for canonical_root in (*roots, *worktree_roots)
            )
        )
        common_dir = (
            self._canonicalizer.canonicalize(observation.git_common_dir)
            if observation.git_common_dir is not None
            else None
        )
        repo_key = (
            _repo_key(common_dir)
            if common_dir is not None and not common_dir.contains_reparse
            else None
        )
        if len(matches) == 1:
            return ProjectResolution(
                observation_id=observation.observation_id,
                state=ProjectResolutionState.RESOLVED,
                project_id=matches[0].project_id,
                repo_key=repo_key,
                canonical_cwd=cwd.display,
            )
        return ProjectResolution(
            observation_id=observation.observation_id,
            state=(
                ProjectResolutionState.CONFLICT if matches else ProjectResolutionState.UNCLASSIFIED
            ),
            project_id=None,
            repo_key=repo_key,
            canonical_cwd=cwd.display,
        )


def _contains(root: CanonicalWindowsPath, candidate: CanonicalWindowsPath) -> bool:
    return candidate.comparison_parts[: len(root.comparison_parts)] == root.comparison_parts


def _contains_reparse(path: Path) -> bool:
    if not path.is_absolute():
        return False
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() or current.is_junction():
            return True
    return False


def _repo_key(common_dir: CanonicalWindowsPath) -> RepoKey:
    comparison_key = "\0".join(common_dir.comparison_parts).encode()
    encoded = base64.b32encode(sha256(comparison_key).digest()).decode("ascii")
    return RepoKey("repo_" + encoded.rstrip("=")[:20])
