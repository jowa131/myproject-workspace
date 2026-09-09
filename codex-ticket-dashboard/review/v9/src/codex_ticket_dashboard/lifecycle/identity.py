"""Registry-only project identity for normalized Hook metadata."""

from hashlib import sha256
from pathlib import Path

from codex_ticket_dashboard.compliance.project_registry import (
    DefaultWindowsPathCanonicalizer,
    ProjectObservation,
    ProjectRegistry,
    ProjectResolution,
)
from codex_ticket_dashboard.config import DashboardConfig
from codex_ticket_dashboard.lifecycle.contracts import lifecycle_project_observation_id
from codex_ticket_dashboard.lifecycle.normalization import NormalizedHook, ObservationError
from codex_ticket_dashboard.storage.path_security import parse_local_fixed_path


def resolve_identity(config: DashboardConfig, hook: NormalizedHook) -> ProjectResolution:
    """Require a real local reparse-free cwd and an exact approved registry match."""
    try:
        path = parse_local_fixed_path(hook.cwd)
        canonicalizer = DefaultWindowsPathCanonicalizer()
        canonical = canonicalizer.canonicalize(path)
        if canonical.contains_reparse or not path.is_dir():
            raise ObservationError(code="PATH_INVALID")
        fingerprint = "sha256:" + sha256(canonical.display.casefold().encode()).hexdigest()
        observation_id = lifecycle_project_observation_id(
            hook.payload.source_host,
            hook.payload.thread_id,
            fingerprint,
        )
        registry = ProjectRegistry(config.projects, canonicalizer)
        return registry.resolve(ProjectObservation(observation_id, Path(canonical.display), None))
    except OSError:
        raise ObservationError(code="PATH_INVALID") from None
