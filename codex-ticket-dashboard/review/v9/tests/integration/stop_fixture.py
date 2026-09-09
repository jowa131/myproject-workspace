import json
from dataclasses import dataclass
from pathlib import Path

from tests.integration.test_lifecycle_projection import fixture

from codex_ticket_dashboard.config import load_dashboard_config
from codex_ticket_dashboard.domain.identifiers import SessionId, TurnId
from codex_ticket_dashboard.domain.source_metadata import McpContextWitness
from codex_ticket_dashboard.ingest.collector import Collector
from codex_ticket_dashboard.lifecycle.admission import observation_envelope
from codex_ticket_dashboard.lifecycle.identity import resolve_identity
from codex_ticket_dashboard.lifecycle.normalization import normalize_hook
from codex_ticket_dashboard.mcp import TicketAdmissionReceipt
from codex_ticket_dashboard.mcp.schemas import TicketPreflightRequest, TicketTurnSummaryRequest
from codex_ticket_dashboard.mcp.tools import EventRecorder
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.path_security import DataRootPaths, data_root_paths


@dataclass(frozen=True, slots=True)
class StopFixture:
    paths: DataRootPaths
    database: Database
    collector: Collector
    config: Path
    raw: bytes
    ticket_id: str


def stop_fixture(root: Path, *, scenario: str = "missing") -> StopFixture:
    root.mkdir(parents=True, exist_ok=True)
    database, collector, writer = fixture(root / "r")
    paths = data_root_paths(root / "r")
    workspace = root / "w"
    workspace.mkdir()
    config = root / "config.toml"
    _ = config.write_text(
        "\n".join(
            (
                "schema_version=1",
                "data_root=" + json.dumps(str(paths.root)),
                "[[projects]]",
                "schema_version=1",
                'project_id="prj_synthetic"',
                'label="Synthetic"',
                "roots=[" + json.dumps(str(workspace)) + "]",
                'wiki_authority="CENTRAL_WIKI"',
                'authority_source_ref="synthetic.md"',
                'authority_source_sha256="' + "a" * 64 + '"',
            )
        ),
        encoding="utf-8",
    )
    hook = normalize_hook(
        json.dumps(
            {
                "session_id": "synthetic",
                "turn_id": "original",
                "cwd": str(workspace),
                "hook_event_name": "UserPromptSubmit",
            }
        ).encode(),
        "host_synthetic",
        "cli",
    )
    observed = observation_envelope(
        hook.payload, resolve_identity(load_dashboard_config(config), hook)
    )
    with database.transaction() as connection:
        _ = connection.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?,1)",
            (
                "prj_synthetic",
                "Synthetic",
                "root_synthetic",
                "repo_synthetic",
                "REGISTRY",
                "sha256:" + "a" * 64,
                1,
            ),
        )
        if scenario != "policy_absent":
            _ = connection.execute(
                "INSERT INTO project_policies VALUES (?,?,?,?,?,?,?,?)",
                (
                    "prj_synthetic",
                    "NOT_APPLICABLE",
                    "NOT_APPLICABLE",
                    "PUSH",
                    "synthetic.md",
                    "sha256:" + "a" * 64,
                    "policy_synthetic",
                    "2026-09-08",
                ),
            )
    _ = writer.write(observed)
    context = {
        "project_observation_id": observed.project_observation_id,
        "project_id": "prj_synthetic",
        "repo_key": observed.repo_key,
        "session_id": "thr_synthetic",
        "turn_id": "original",
    }
    preflight = TicketPreflightRequest.model_validate(
        {
            "context": context,
            "disposition": "NEW_TICKET",
            "classification": "TASK",
            "goal": "Synthetic",
            "non_goals": [],
            "acceptance_criteria": ["Synthetic"],
            "declared_git_requirement": "NOT_APPLICABLE",
            "declared_wiki_requirement": "NOT_APPLICABLE",
        }
    )
    witness = McpContextWitness(
        source_host="host_synthetic",
        thread_id=SessionId("thr_synthetic"),
        turn_id=TurnId("original"),
    )
    recorder = EventRecorder(writer)
    ticket = recorder.record(preflight, witness=witness)
    assert isinstance(ticket, TicketAdmissionReceipt)
    _ = collector.startup_scan()
    if scenario in {"complete", "pending", "review_unverified"}:
        summary = TicketTurnSummaryRequest.model_validate(
            {
                "context": context,
                "ticket_id": ticket.ticket_id,
                "request_feedback_summary": "Synthetic",
                "outcome": "Synthetic",
                "change_surface": [],
                "verification": [],
                "blockers": [],
                "user_decisions": [],
                "next_step": "Synthetic",
                "affected_work_item_ids": [],
                "proposed_status": "IN_REVIEW"
                if scenario == "review_unverified"
                else "IN_PROGRESS",
            }
        )
        _ = recorder.record(summary, witness=witness)
        if scenario != "pending":
            _ = collector.startup_scan()
    raw = json.dumps(
        {
            "session_id": "synthetic",
            "turn_id": "original",
            "cwd": str(workspace),
            "hook_event_name": "Stop",
            "stop_hook_active": scenario == "active",
            "last_assistant_message": "CANARY_PRIVATE_RAW",
        }
    ).encode()
    return StopFixture(paths, database, collector, config, raw, ticket.ticket_id)
