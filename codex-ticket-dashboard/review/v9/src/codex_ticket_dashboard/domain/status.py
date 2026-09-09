"""Ticket and work-item state authority decisions."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum, unique
from types import MappingProxyType
from typing import Final, Literal, assert_never

from codex_ticket_dashboard.domain.events import ActorType


@unique
class TicketStatus(StrEnum):
    """Ticket projection states."""

    BACKLOG = "BACKLOG"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_USER = "WAITING_USER"
    BLOCKED = "BLOCKED"
    IN_REVIEW = "IN_REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@unique
class WorkItemStatus(StrEnum):
    """Task and subtask projection states."""

    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_USER = "WAITING_USER"
    BLOCKED = "BLOCKED"
    RESULT_REPORTED = "RESULT_REPORTED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


@unique
class StatusAuthority(StrEnum):
    """Authorities accepted by ticket and work-item state transitions."""

    CODEX_PREFLIGHT = "CODEX_PREFLIGHT"
    CODEX_EXECUTION = "CODEX_EXECUTION"
    CODEX_RESULT = "CODEX_RESULT"
    USER_EXPLICIT = "USER_EXPLICIT"
    SYSTEM_DERIVED = "SYSTEM_DERIVED"


@unique
class UserDecision(StrEnum):
    """Explicit user decision variants."""

    ACCEPT = "ACCEPT"
    CANCEL = "CANCEL"
    REOPEN = "REOPEN"
    SCOPE_CHANGE = "SCOPE_CHANGE"


@dataclass(frozen=True, slots=True)
class TicketTransition:
    """Complete authority context for one requested ticket transition."""

    from_status: TicketStatus
    to_status: TicketStatus
    authority: StatusAuthority
    actor_type: ActorType
    decision: UserDecision | None = None
    decision_is_fresh: bool = False
    decision_is_consumed: bool = False
    has_causation: bool = False


@dataclass(frozen=True, slots=True)
class WorkItemRemoval:
    """Authority context for removing a work item from the active set."""

    to_status: WorkItemStatus
    authority: StatusAuthority
    actor_type: ActorType
    decision: UserDecision | None
    decision_is_fresh: bool
    decision_is_consumed: bool


@dataclass(frozen=True, slots=True)
class TransitionAllowed:
    """Successful state authority decision."""

    code: Literal["ALLOWED"] = "ALLOWED"


@dataclass(frozen=True, slots=True)
class TransitionRejected:
    """Rejected state authority decision."""

    code: Literal["STATUS_AUTHORITY_REJECTED"] = "STATUS_AUTHORITY_REJECTED"


type TransitionResult = TransitionAllowed | TransitionRejected


@dataclass(frozen=True, slots=True)
class AuthorityRule:
    """Transition rule requiring one of a closed set of authorities."""

    authorities: frozenset[StatusAuthority]
    actor_type: ActorType | None = None
    causation_required: bool = False


@dataclass(frozen=True, slots=True)
class DecisionRule:
    """Transition rule requiring a fresh explicit user decision."""

    decisions: frozenset[UserDecision]


type TransitionRule = AuthorityRule | DecisionRule

_RULES: Final[Mapping[tuple[TicketStatus, TicketStatus], TransitionRule]] = MappingProxyType(
    {
        (TicketStatus.BACKLOG, TicketStatus.PLANNED): AuthorityRule(
            frozenset({StatusAuthority.CODEX_PREFLIGHT})
        ),
        (TicketStatus.PLANNED, TicketStatus.IN_PROGRESS): AuthorityRule(
            frozenset({StatusAuthority.CODEX_EXECUTION})
        ),
        (TicketStatus.IN_PROGRESS, TicketStatus.WAITING_USER): AuthorityRule(
            frozenset({StatusAuthority.CODEX_RESULT})
        ),
        (TicketStatus.IN_PROGRESS, TicketStatus.BLOCKED): AuthorityRule(
            frozenset({StatusAuthority.CODEX_RESULT})
        ),
        (TicketStatus.IN_PROGRESS, TicketStatus.IN_REVIEW): AuthorityRule(
            frozenset({StatusAuthority.CODEX_RESULT})
        ),
        (TicketStatus.WAITING_USER, TicketStatus.IN_PROGRESS): AuthorityRule(
            frozenset({StatusAuthority.CODEX_EXECUTION, StatusAuthority.USER_EXPLICIT})
        ),
        (TicketStatus.BLOCKED, TicketStatus.IN_PROGRESS): AuthorityRule(
            frozenset({StatusAuthority.CODEX_EXECUTION, StatusAuthority.USER_EXPLICIT})
        ),
        (TicketStatus.IN_REVIEW, TicketStatus.BLOCKED): AuthorityRule(
            frozenset({StatusAuthority.SYSTEM_DERIVED}),
            actor_type=ActorType.SYSTEM,
            causation_required=True,
        ),
        (TicketStatus.BLOCKED, TicketStatus.IN_REVIEW): AuthorityRule(
            frozenset({StatusAuthority.CODEX_RESULT})
        ),
        (TicketStatus.IN_REVIEW, TicketStatus.IN_PROGRESS): DecisionRule(
            frozenset({UserDecision.SCOPE_CHANGE, UserDecision.REOPEN})
        ),
        (TicketStatus.IN_REVIEW, TicketStatus.COMPLETED): DecisionRule(
            frozenset({UserDecision.ACCEPT})
        ),
        (TicketStatus.COMPLETED, TicketStatus.PLANNED): DecisionRule(
            frozenset({UserDecision.REOPEN, UserDecision.SCOPE_CHANGE})
        ),
        (TicketStatus.CANCELLED, TicketStatus.PLANNED): DecisionRule(
            frozenset({UserDecision.REOPEN})
        ),
        **{
            (source, TicketStatus.CANCELLED): DecisionRule(frozenset({UserDecision.CANCEL}))
            for source in (
                TicketStatus.BACKLOG,
                TicketStatus.PLANNED,
                TicketStatus.IN_PROGRESS,
                TicketStatus.WAITING_USER,
                TicketStatus.BLOCKED,
                TicketStatus.IN_REVIEW,
            )
        },
    }
)


def evaluate_ticket_transition(transition: TicketTransition) -> TransitionResult:
    """Apply the exact transition authority matrix without mutating state."""
    rule = _RULES.get((transition.from_status, transition.to_status))
    if rule is None:
        return TransitionRejected()
    match rule:
        case AuthorityRule(authorities=authorities, actor_type=actor, causation_required=required):
            authorized = transition.authority in authorities
            actor_matches = actor is None or transition.actor_type is actor
            causation_matches = not required or transition.has_causation
            if authorized and actor_matches and causation_matches:
                return TransitionAllowed()
            return TransitionRejected()
        case DecisionRule(decisions=decisions):
            decision_matches = transition.decision in decisions
            if (
                transition.authority is StatusAuthority.USER_EXPLICIT
                and transition.actor_type is ActorType.USER
                and decision_matches
                and transition.decision_is_fresh
                and not transition.decision_is_consumed
            ):
                return TransitionAllowed()
            return TransitionRejected()
        case unreachable:
            assert_never(unreachable)


def evaluate_work_item_removal(removal: WorkItemRemoval) -> TransitionResult:
    """Require a fresh user decision before shrinking the active work-item set."""
    match removal.to_status:
        case WorkItemStatus.CANCELLED:
            required_decision = UserDecision.CANCEL
        case WorkItemStatus.SUPERSEDED:
            required_decision = UserDecision.SCOPE_CHANGE
        case (
            WorkItemStatus.PLANNED
            | WorkItemStatus.IN_PROGRESS
            | WorkItemStatus.WAITING_USER
            | WorkItemStatus.BLOCKED
            | WorkItemStatus.RESULT_REPORTED
        ):
            return TransitionRejected()
        case unreachable:
            assert_never(unreachable)
    if (
        removal.authority is StatusAuthority.USER_EXPLICIT
        and removal.actor_type is ActorType.USER
        and removal.decision is required_decision
        and removal.decision_is_fresh
        and not removal.decision_is_consumed
    ):
        return TransitionAllowed()
    return TransitionRejected()


@dataclass(frozen=True, slots=True)
class AggregateRequest:
    """Current ticket state and all projected work-item states."""

    current_ticket_status: TicketStatus
    work_item_statuses: tuple[WorkItemStatus, ...]


@dataclass(frozen=True, slots=True)
class AggregateCandidate:
    """Highest-priority ticket status proposed by active work items."""

    proposed_status: TicketStatus


@dataclass(frozen=True, slots=True)
class NoActiveWorkItems:
    """Warning outcome that preserves the current ticket state."""

    ticket_status_unchanged: TicketStatus
    code: Literal["NO_ACTIVE_WORK_ITEMS"] = "NO_ACTIVE_WORK_ITEMS"


@dataclass(frozen=True, slots=True)
class AggregateUnchanged:
    """Outcome for active work that has no aggregate status candidate yet."""

    ticket_status_unchanged: TicketStatus
    code: Literal["NO_CANDIDATE"] = "NO_CANDIDATE"


type AggregateResult = AggregateCandidate | NoActiveWorkItems | AggregateUnchanged


def aggregate_work_items(request: AggregateRequest) -> AggregateResult:
    """Apply IN_PROGRESS, WAITING_USER, BLOCKED, IN_REVIEW priority in order."""
    active = tuple(
        status
        for status in request.work_item_statuses
        if status not in {WorkItemStatus.CANCELLED, WorkItemStatus.SUPERSEDED}
    )
    if not active:
        return NoActiveWorkItems(ticket_status_unchanged=request.current_ticket_status)
    priority = (
        (WorkItemStatus.IN_PROGRESS, TicketStatus.IN_PROGRESS),
        (WorkItemStatus.WAITING_USER, TicketStatus.WAITING_USER),
        (WorkItemStatus.BLOCKED, TicketStatus.BLOCKED),
    )
    for work_status, ticket_status in priority:
        if work_status in active:
            return AggregateCandidate(proposed_status=ticket_status)
    if all(status is WorkItemStatus.RESULT_REPORTED for status in active):
        return AggregateCandidate(proposed_status=TicketStatus.IN_REVIEW)
    return AggregateUnchanged(ticket_status_unchanged=request.current_ticket_status)
