"""Recording completeness policy independent from ticket completion authority."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from codex_ticket_dashboard.compliance.policy_resolver import GitRequirement, WikiRequirement
from codex_ticket_dashboard.lifecycle.contracts import MissingRequirement
from codex_ticket_dashboard.storage.turn_recording import TurnFact, TurnRecording

type RecordingState = Literal["COMPLETE", "MISSING", "PENDING", "UNVERIFIED", "BLOCKED"]


@dataclass(frozen=True, slots=True)
class AppliedRequirements:
    """Requirements resolved from the applied ticket project policy, never caller authority."""

    git: GitRequirement
    wiki: WikiRequirement


@dataclass(frozen=True, slots=True)
class StopAssessment:
    """Only MISSING is eligible for one request; no state authorizes ticket closure."""

    state: RecordingState
    missing_requirements: tuple[MissingRequirement, ...] = ()

    @property
    def request_eligible(self) -> bool:
        """Pending, failed and unverified facts must not trigger duplicate regeneration."""
        return self.state == "MISSING"


def assess_turn(
    recording: TurnRecording,
    pending_types: frozenset[str],
    *,
    review_verified: bool = True,
    requirements: AppliedRequirements | None = None,
    original: TurnRecording | None = None,
) -> StopAssessment:
    """Require exact applied preflight, summary and applicable successful gate evidence."""
    if pending_types:
        return StopAssessment("PENDING", ("PENDING_INGEST",))
    if (
        not recording.facts
        or not review_verified
        or requirements is None
        or (original is not None and not original.facts)
    ):
        return StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    tickets = {fact.ticket_id for fact in recording.facts if fact.ticket_id is not None}
    if len(tickets) != 1:
        return StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    latest = {fact.event_type: fact for fact in recording.facts}
    if original is not None:
        for tag in ("TICKET_PREFLIGHT_RECORDED", "TICKET_LINKED_TO_THREAD", "TICKET_CREATED"):
            _ = latest.pop(tag, None)
        latest.update(
            {
                fact.event_type: fact
                for fact in original.facts
                if fact.event_type
                in {"TICKET_PREFLIGHT_RECORDED", "TICKET_LINKED_TO_THREAD", "TICKET_CREATED"}
            }
        )
    return _assess_applied(latest, requirements)


def _assess_applied(
    latest: Mapping[str, TurnFact],
    requirements: AppliedRequirements,
) -> StopAssessment:
    preflight = (
        latest.get("TICKET_PREFLIGHT_RECORDED")
        or latest.get("TICKET_LINKED_TO_THREAD")
        or latest.get("TICKET_CREATED")
    )
    if preflight is None:
        return StopAssessment("MISSING", ("PREFLIGHT",))
    if (
        preflight.classification not in {"TASK", "DISCUSSION"}
        or preflight.declared_git_requirement
        not in {"NOT_APPLICABLE", "STATUS_ONLY", "COMMIT", "PUSH"}
        or preflight.declared_wiki_requirement
        not in {"NOT_APPLICABLE", "CENTRAL_WIKI", "PROJECT_LOCAL_WIKI"}
    ):
        return StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    if (
        preflight.declared_git_requirement != requirements.git
        or preflight.declared_wiki_requirement != requirements.wiki
    ):
        return StopAssessment("UNVERIFIED", ("POLICY_DECLARATION_MISMATCH",))
    missing: list[MissingRequirement] = []
    if "TURN_SUMMARIZED" not in latest:
        missing.append("TURN_SUMMARY")
    gates: tuple[tuple[MissingRequirement, str, str], ...] = (
        ("GIT_GATE", "GIT_GATE_REPORTED", preflight.declared_git_requirement),
        ("WIKI_GATE", "WIKI_GATE_REPORTED", preflight.declared_wiki_requirement),
    )
    for requirement, tag, declared in gates:
        if declared == "NOT_APPLICABLE":
            continue
        gate = latest.get(tag)
        if gate is None:
            missing.append(requirement)
            continue
        if gate.resolved_requirement != declared:
            return StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
        if not _gate_satisfied(gate, declared):
            return StopAssessment("BLOCKED")
    return StopAssessment("MISSING", tuple(missing)) if missing else StopAssessment("COMPLETE")


def _gate_satisfied(gate: TurnFact, declared: str) -> bool:
    expected = "STATUS-ONLY" if declared == "STATUS_ONLY" else "SATISFIED"
    return gate.result == expected
