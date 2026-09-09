"""Public page-model boundary for template data."""

from dataclasses import dataclass

from codex_ticket_dashboard.web.api_models import (
    ComplianceGate,
    IngestIssue,
    ProjectItem,
    TicketItem,
)


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    """Safe summary values for server-rendered screen templates."""

    projects: tuple[ProjectItem, ...]
    tickets: tuple[TicketItem, ...]
    gates: tuple[ComplianceGate, ...]
    issues: tuple[IngestIssue, ...]
    watermark: int

    @property
    def triage_count(self) -> int:
        """Count structured tickets requiring triage."""
        return sum(ticket.needs_triage for ticket in self.tickets)

    @property
    def unresolved_identity_issues(self) -> tuple[IngestIssue, ...]:
        """Return open identity-related collector issues."""
        return tuple(
            issue
            for issue in self.issues
            if issue.state == "OPEN"
            and (
                issue.field_path == "project_id"
                or issue.code in {"IDENTITY_CONFLICT", "UNCLASSIFIED"}
            )
        )

    @property
    def policy_warnings(self) -> tuple[ComplianceGate, ...]:
        """Return current gates that are not satisfied."""
        return tuple(gate for gate in self.gates if gate.status not in {"SATISFIED", "N/A"})

    @property
    def policy_issues(self) -> tuple[IngestIssue, ...]:
        """Return open policy mismatch or drift issues."""
        return tuple(
            issue
            for issue in self.issues
            if issue.state == "OPEN" and issue.code in {"POLICY_MISMATCH", "POLICY_DRIFT"}
        )

    @property
    def stale_database_issues(self) -> tuple[IngestIssue, ...]:
        """Return open stale database collector issues."""
        return tuple(
            issue
            for issue in self.issues
            if issue.state == "OPEN" and issue.code in {"STALE_DB", "STALE_DATABASE"}
        )

    @property
    def dependency_issues(self) -> tuple[IngestIssue, ...]:
        """Return open dependency pending or failure issues."""
        return tuple(
            issue
            for issue in self.issues
            if issue.state == "OPEN" and issue.code in {"DEPENDENCY_PENDING", "DEPENDENCY_FAILED"}
        )
