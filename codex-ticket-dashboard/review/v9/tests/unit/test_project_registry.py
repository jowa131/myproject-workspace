from pathlib import Path
from collections import Counter
from hashlib import sha256
import json

from codex_ticket_dashboard.compliance.project_registry import (
    CanonicalWindowsPath,
    DefaultWindowsPathCanonicalizer,
    ProjectObservation,
    ProjectRegistry,
)
from codex_ticket_dashboard.config import ProjectRegistryEntry
from codex_ticket_dashboard.domain.events import ProjectResolutionState
from codex_ticket_dashboard.domain.identifiers import ProjectObservationId


def test_registry_entry_preserves_project_and_repo_identity_inputs() -> None:
    # Given
    raw_entry = {
        "schema_version": 1,
        "project_id": "prj_dashboard",
        "label": "Dashboard",
        "roots": [r"C:\MyProject\codex-ticket-dashboard"],
        "worktree_roots": [r"D:\Worktrees\Dashboard"],
        "wiki_authority": "CENTRAL_WIKI",
        "authority_source_ref": "wiki/knowledge/dashboard.md",
        "authority_source_sha256": "a" * 64,
    }

    # When
    entry = ProjectRegistryEntry.model_validate(raw_entry)

    # Then
    assert entry.project_id == "prj_dashboard"
    assert tuple(str(path) for path in entry.roots) == (r"C:\MyProject\codex-ticket-dashboard",)


def test_nested_case_and_separator_variants_resolve_without_changing_display_case() -> None:
    # Given
    entry = _entry(
        "prj_dashboard",
        roots=(Path(r"C:\MyProject\Codex-Ticket-Dashboard"),),
    )
    registry = ProjectRegistry((entry,))
    observation = ProjectObservation(
        observation_id=ProjectObservationId("pobs_12345678-1234-4234-8234-1234567890ab"),
        cwd=Path("c:/myproject/codex-ticket-dashboard/src"),
        git_common_dir=Path(r"C:\MyProject\.git"),
    )

    # When
    result = registry.resolve(observation)

    # Then
    assert result.state is ProjectResolutionState.RESOLVED
    assert result.project_id == "prj_dashboard"
    assert result.canonical_cwd is not None
    assert "codex-ticket-dashboard" in result.canonical_cwd.casefold()
    assert result.repo_key is not None
    assert result.repo_key != result.project_id


def test_worktree_alias_resolves_to_same_project_and_repo_key() -> None:
    # Given
    registry = ProjectRegistry(
        (_entry("prj_dashboard", worktree_roots=(Path(r"D:\Worktrees\Dashboard"),)),)
    )
    common_dir = Path(r"C:\SyntheticRepo\.git")
    main = ProjectObservation(
        ProjectObservationId("pobs_12345678-1234-4234-8234-1234567890ab"),
        Path(r"C:\MyProject\codex-ticket-dashboard"),
        common_dir,
    )
    worktree = ProjectObservation(
        ProjectObservationId("pobs_22345678-1234-4234-8234-1234567890ab"),
        Path(r"D:\Worktrees\Dashboard\feature-a"),
        Path(r"c:\syntheticrepo\.GIT"),
    )

    # When
    resolutions = (registry.resolve(main), registry.resolve(worktree))

    # Then
    assert tuple(item.project_id for item in resolutions) == ("prj_dashboard", "prj_dashboard")
    assert resolutions[0].repo_key == resolutions[1].repo_key


def test_multiple_or_absent_matches_fail_closed() -> None:
    # Given
    registry = ProjectRegistry(
        (
            _entry("prj_parent", roots=(Path(r"C:\Workspace"),)),
            _entry("prj_child", roots=(Path(r"C:\Workspace\Child"),)),
        )
    )
    conflict = ProjectObservation(
        ProjectObservationId("pobs_12345678-1234-4234-8234-1234567890ab"),
        Path(r"C:\Workspace\Child\src"),
        None,
    )
    absent = ProjectObservation(
        ProjectObservationId("pobs_22345678-1234-4234-8234-1234567890ab"),
        Path(r"D:\Elsewhere"),
        None,
    )
    relative = ProjectObservation(
        ProjectObservationId("pobs_32345678-1234-4234-8234-1234567890ab"),
        Path("relative-project"),
        None,
    )
    junction_registry = ProjectRegistry(
        (_entry("prj_junction_target", roots=(Path(r"C:\Workspace\Child"),)),),
        _SyntheticJunctionCanonicalizer(),
    )
    junction = ProjectObservation(
        ProjectObservationId("pobs_42345678-1234-4234-8234-1234567890ab"),
        Path(r"C:\SyntheticJunction\src"),
        None,
    )

    # When
    results = (
        registry.resolve(conflict),
        registry.resolve(absent),
        registry.resolve(relative),
        junction_registry.resolve(junction),
    )

    # Then
    assert tuple(item.state for item in results) == (
        ProjectResolutionState.CONFLICT,
        ProjectResolutionState.UNCLASSIFIED,
        ProjectResolutionState.UNCLASSIFIED,
        ProjectResolutionState.UNCLASSIFIED,
    )
    assert all(item.project_id is None for item in results)


class _SyntheticJunctionCanonicalizer:
    def canonicalize(self, path: Path) -> CanonicalWindowsPath:
        rendered = str(path)
        if rendered.casefold().startswith(r"c:\syntheticjunction"):
            suffix = rendered[len(r"C:\SyntheticJunction") :]
            canonical = DefaultWindowsPathCanonicalizer().canonicalize(
                Path(r"C:\Workspace\Child" + suffix)
            )
            return CanonicalWindowsPath(
                canonical.display,
                canonical.comparison_parts,
                contains_reparse=True,
            )
        return DefaultWindowsPathCanonicalizer().canonicalize(path)


def _entry(
    project_id: str,
    *,
    roots: tuple[Path, ...] | None = None,
    worktree_roots: tuple[Path, ...] = (),
) -> ProjectRegistryEntry:
    actual_roots = roots or (Path(r"C:\MyProject\codex-ticket-dashboard"),)
    return ProjectRegistryEntry.model_validate(
        {
            "schema_version": 1,
            "project_id": project_id,
            "label": project_id,
            "roots": actual_roots,
            "worktree_roots": worktree_roots,
            "wiki_authority": "CENTRAL_WIKI",
            "authority_source_ref": "wiki/knowledge/dashboard.md",
            "authority_source_sha256": "a" * 64,
        }
    )


class _CountingCanonicalizer:
    def __init__(self, reparse_root: Path | None = None) -> None:
        self.calls: Counter[Path] = Counter()
        self.reparse_root = reparse_root

    def canonicalize(self, path: Path) -> CanonicalWindowsPath:
        self.calls[path] += 1
        canonical = DefaultWindowsPathCanonicalizer().canonicalize(path)
        return CanonicalWindowsPath(
            canonical.display, canonical.comparison_parts,
            path == self.reparse_root and self.calls[path] == 1,
        )


def test_registered_paths_are_reused_with_unchanged_snapshot_digest() -> None:
    canonicalizer = _CountingCanonicalizer()
    entries = (
        _entry("prj_z", roots=(Path(r"C:\Synthetic\z"),)),
        _entry("prj_a", roots=(Path(r"C:\Synthetic\a"),),
               worktree_roots=(Path(r"D:\Synthetic\alias"),)),
    )
    registry = ProjectRegistry(entries, canonicalizer)
    observation = ProjectObservation(
        ProjectObservationId("pobs_12345678-1234-4234-8234-1234567890ab"),
        Path(r"D:\Synthetic\alias\src"), None,
    )
    for _ in range(2):
        assert registry.resolve(observation).project_id == "prj_a"
    assert all(canonicalizer.calls[root] == 1 for entry in entries
               for root in (*entry.roots, *entry.worktree_roots))
    assert canonicalizer.calls[observation.cwd] == 2
    serialized = json.dumps([
        {
            "authority_source_ref": entry.authority_source_ref,
            "authority_source_sha256": entry.authority_source_sha256,
            "label": entry.label,
            "project_id": entry.project_id,
            "roots": tuple(DefaultWindowsPathCanonicalizer().canonicalize(root).display
                           for root in entry.roots),
            "schema_version": entry.schema_version,
            "wiki_authority": entry.wiki_authority,
            "worktree_roots": tuple(DefaultWindowsPathCanonicalizer().canonicalize(root).display
                                    for root in entry.worktree_roots),
        } for entry in sorted(entries, key=lambda entry: entry.project_id)
    ], ensure_ascii=True, separators=(",", ":")).encode()
    digest = "sha256:" + sha256(serialized).hexdigest()
    assert registry.snapshot.digest == digest
    assert registry.snapshot.snapshot_id == "reg_" + digest[7:31]
    assert tuple(project.project_id for project in registry.snapshot.projects) == ("prj_a", "prj_z")


def test_original_reparse_flag_and_duplicate_entries_are_preserved() -> None:
    root = Path(r"C:\Synthetic\root")
    observation = ProjectObservation(
        ProjectObservationId("pobs_12345678-1234-4234-8234-1234567890ab"),
        root / "src", None,
    )
    canonicalizer = _CountingCanonicalizer(root)
    registry = ProjectRegistry((_entry("prj_same", roots=(root,)),), canonicalizer)
    assert registry.resolve(observation).state is ProjectResolutionState.UNCLASSIFIED
    assert canonicalizer.calls[root] == 1
    duplicated = ProjectRegistry((
        _entry("prj_same", roots=(root,)),
        _entry("prj_same", roots=(root / "src",)),
    ))
    assert len(duplicated.snapshot.projects) == 2
    assert duplicated.resolve(observation).state is ProjectResolutionState.CONFLICT
