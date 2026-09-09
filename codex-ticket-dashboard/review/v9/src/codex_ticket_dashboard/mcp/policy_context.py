"""Server-generated machine metadata from exact applied project and policy rows."""

from typing import ClassVar, Final, Literal, Self

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, JsonValue, TypeAdapter, ValidationError

from codex_ticket_dashboard.compliance.policy_resolver import (
    GitRequirement,
    ProjectPolicy,
    WikiRequirement,
)
from codex_ticket_dashboard.compliance.runtime_authority_models import Digest as PolicySourceDigest
from codex_ticket_dashboard.compliance.wiki_gate import (
    WikiEvidence,
    WikiFileEvidence,
    evaluate_wiki_gate,
)
from codex_ticket_dashboard.domain.events import ValidatedPayloadDigest
from codex_ticket_dashboard.ingest.payload_models import SafeItem
from codex_ticket_dashboard.mcp.schemas import WikiUpdateRecordRequest
from codex_ticket_dashboard.storage.path_security import DataRootPaths
from codex_ticket_dashboard.storage.readonly_observation import read_observation_database


class ObserverContext(BaseModel):
    """Source tuple and resolved registry fields read from accepted observations."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    source_host: str
    thread_id: str
    turn_id: str | None
    parent_thread_id: str | None
    relation_state: str
    project_observation_id: str
    project_id: str | None
    repo_key: str | None

    def with_applied_repository(self, paths: DataRootPaths) -> Self:
        """Return enriched context without changing the immutable source observation."""
        return self.model_copy(
            update={
                "repo_key": applied_repository(paths, self.project_id, self.repo_key),
            }
        )


type RepositoryRow = tuple[SafeItem, Literal["REGISTRY"], ValidatedPayloadDigest]
type PolicyRow = tuple[
    WikiRequirement,
    GitRequirement,
    GitRequirement,
    SafeItem,
    PolicySourceDigest | ValidatedPayloadDigest,
    SafeItem,
]
_REPOSITORY: Final[TypeAdapter[RepositoryRow | None]] = TypeAdapter(RepositoryRow | None)
_POLICY: Final[TypeAdapter[PolicyRow | None]] = TypeAdapter(PolicyRow | None)
GENERATED_FIELDS: Final[dict[str, frozenset[str]]] = {
    "GitGateReportRequest": frozenset(
        {
            "policy_snapshot_id",
            "resolved_requirement",
            "authority_source",
            "authority_ceiling",
            "repo_key",
        }
    ),
    "WikiUpdateRecordRequest": frozenset(
        {
            "policy_snapshot_id",
            "resolved_requirement",
            "wiki_root_kind",
        }
    ),
}


def applied_repository(
    paths: DataRootPaths, project: str | None, observed: str | None
) -> str | None:
    """Enrich an accepted project tuple, rejecting any conflicting existing repository claim."""
    path = paths.data / "dashboard.sqlite3"
    if project is None or not path.exists():
        return observed
    try:
        with read_observation_database(path, paths.root) as connection:
            row = _REPOSITORY.validate_python(
                connection.execute(
                    "SELECT repo_key,identity_source,identity_source_hash FROM projects WHERE id=?",
                    (project,),
                ).fetchone()
            )
    except (OSError, ValidationError):
        message = "PROJECT_REGISTRY_CONFLICT"
        raise ToolError(message) from None
    if row is None:
        return observed
    if observed is not None and observed != row[0]:
        message = "PROJECT_REGISTRY_CONFLICT"
        raise ToolError(message)
    return row[0]


def bind_policy_fields(
    paths: DataRootPaths,
    request: dict[str, JsonValue],
    project: str,
    repo_key: str | None,
    tool_name: str | None,
) -> dict[str, JsonValue]:
    """Fill applied machine metadata while retaining caller evidence and declared applicability."""
    if tool_name not in {"git_gate_report", "wiki_update_record", "ticket_preflight_record"}:
        return request
    try:
        with read_observation_database(paths.data / "dashboard.sqlite3", paths.root) as connection:
            row = _POLICY.validate_python(
                connection.execute(
                    """SELECT pp.wiki_authority,pp.git_authority,pp.authority_ceiling,
                pp.evidence_ref,pp.evidence_hash,pp.policy_snapshot_id
                FROM project_policies pp JOIN projects p ON p.id=pp.project_id WHERE p.id=?""",
                    (project,),
                ).fetchone()
            )
    except (OSError, ValidationError):
        message = "POLICY_CONTEXT_UNVERIFIED"
        raise ToolError(message) from None
    if row is None:
        message = "POLICY_CONTEXT_UNVERIFIED"
        raise ToolError(message)
    wiki, git, ceiling, source, _source_hash, snapshot = row
    if tool_name == "ticket_preflight_record":
        if (
            request.get("declared_git_requirement") != git.value
            or request.get("declared_wiki_requirement") != wiki.value
        ):
            message = f"PREFLIGHT_POLICY_DECLARATION_MISMATCH: expected_git={git.value}"
            message += f" expected_wiki={wiki.value}"
            raise ToolError(message)
        return request
    requirement = git if tool_name == "git_gate_report" else wiki
    if request.get("declared_requirement") != requirement.value:
        message = f"POLICY_DECLARATION_MISMATCH: expected={requirement.value}"
        raise ToolError(message)
    generated: dict[str, JsonValue] = {
        "policy_snapshot_id": snapshot,
        "resolved_requirement": requirement.value,
    }
    if tool_name == "git_gate_report":
        if repo_key is None:
            message = "PROJECT_IDENTITY_UNVERIFIED"
            raise ToolError(message)
        generated.update(
            authority_source=source, authority_ceiling=ceiling.value, repo_key=repo_key
        )
    else:
        generated["wiki_root_kind"] = (
            "CENTRAL" if wiki is WikiRequirement.CENTRAL_WIKI else "PROJECT_LOCAL"
        )
    if any(key in request and request[key] != value for key, value in generated.items()):
        message = "MODEL_POLICY_CONTEXT_CONFLICT"
        raise ToolError(message)
    bound = {**request, **generated}
    _check_wiki_result(bound, row, tool_name)
    return bound


def _check_wiki_result(
    request: dict[str, JsonValue],
    row: PolicyRow,
    tool_name: str | None,
) -> None:
    if tool_name != "wiki_update_record":
        return
    parsed = WikiUpdateRecordRequest.model_validate(request)
    wiki, git, ceiling, source, source_hash, snapshot = row
    policy = ProjectPolicy(
        parsed.context.project_id,
        git,
        ceiling,
        wiki,
        source,
        source_hash,
        snapshot,
        source_hash,
    )
    evidence = WikiEvidence(
        files=tuple(
            WikiFileEvidence(path, parsed.sha256_before[str(path)], parsed.sha256_after[str(path)])
            for path in parsed.relative_paths
        ),
        section_markers=parsed.section_markers,
        required_fields_present=parsed.required_fields_present,
        strict_utf8_ok=parsed.strict_utf8_ok,
        generated_projection_target=False,
    )
    assessment = evaluate_wiki_gate(policy, parsed.declared_requirement, evidence)
    if assessment.status != parsed.result:
        message = f"WIKI_RESULT_MISMATCH: expected={assessment.status.value}"
        raise ToolError(message)
