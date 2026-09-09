"""Current recording gaps from explicit related facts and applied project requirements."""

import sqlite3
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.compliance.policy_resolver import GitRequirement, WikiRequirement
from codex_ticket_dashboard.lifecycle.completeness import (
    AppliedRequirements,
    StopAssessment,
    assess_turn,
)
from codex_ticket_dashboard.lifecycle.review_evidence import review_is_verified
from codex_ticket_dashboard.storage.related_recording import read_related_recording
from codex_ticket_dashboard.storage.turn_recording import TurnKey

_POLICY: Final[TypeAdapter[tuple[GitRequirement, WikiRequirement] | None]] = TypeAdapter(
    tuple[GitRequirement, WikiRequirement] | None,
)


def assess_recording(connection: sqlite3.Connection, key: TurnKey, high: int) -> StopAssessment:
    """A causal binding supplies related evidence, never a successful gate or user decision."""
    related = read_related_recording(connection, key, high)
    if related.relation_unverified:
        return StopAssessment("UNVERIFIED", ("IDENTITY_UNVERIFIED",))
    recording = related.combined
    tickets = {fact.ticket_id for fact in recording.facts if fact.ticket_id is not None}
    policy = (
        None
        if len(tickets) != 1
        else _POLICY.validate_python(
            connection.execute(
                """SELECT p.git_authority,p.wiki_authority FROM tickets t
                JOIN project_policies p ON p.project_id=t.project_id WHERE t.id=?""",
                (next(iter(tickets)),),
            ).fetchone()
        )
    )
    requirements = None if policy is None else AppliedRequirements(*policy)
    return assess_turn(
        recording,
        frozenset(),
        requirements=requirements,
        original=related.original,
        review_verified=review_is_verified(connection, recording, high),
    )
