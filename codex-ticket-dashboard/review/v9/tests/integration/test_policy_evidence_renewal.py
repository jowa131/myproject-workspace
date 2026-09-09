import json
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import JsonValue, TypeAdapter
from runtime_bootstrap_fixtures import Fixture, fixture

from codex_ticket_dashboard.compliance.runtime_authority_models import RuntimeAuthorityError
from codex_ticket_dashboard.compliance.runtime_preflight import preflight_runtime
from codex_ticket_dashboard.ingest.authority_models import next_ingest_sequence
from codex_ticket_dashboard.ingest.runtime_bootstrap_state import RuntimeBootstrapAction
from codex_ticket_dashboard.runtime import create_runtime
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.models import DatabaseConfig
from codex_ticket_dashboard.storage.readonly_observation import read_observation_database

_JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


@dataclass(frozen=True, slots=True)
class RenewalPins:
    previous_evidence_hash: str
    previous_policy_snapshot_id: str


def _database_path(configured: Fixture) -> Path:
    return configured.root / "data/dashboard.sqlite3"


def _existing_pins(configured: Fixture) -> RenewalPins:
    with read_observation_database(_database_path(configured), configured.root) as connection:
        row = connection.execute(
            "SELECT evidence_hash,policy_snapshot_id FROM project_policies"
        ).fetchone()
    assert row is not None
    return RenewalPins(str(row[0]), str(row[1]))


def _renewed_authority(configured: Fixture, pins: RenewalPins | None) -> str:
    project_policy = configured.authority.parent / "project.md"
    _ = project_policy.write_text("Synthetic project policy renewed", encoding="utf-8")
    declaration = _JSON_OBJECT.validate_json(configured.authority.read_bytes())
    policy_sources = declaration["policy_sources"]
    assert isinstance(policy_sources, list)
    for source in policy_sources:
        assert isinstance(source, dict)
        if source["role"] == "project":
            source["sha256"] = sha256(project_policy.read_bytes()).hexdigest()
    if pins is not None:
        declaration["policy_evidence_renewal"] = {
            "previous_evidence_hash": pins.previous_evidence_hash,
            "previous_policy_snapshot_id": pins.previous_policy_snapshot_id,
        }
    _ = configured.authority.write_text(json.dumps(declaration), encoding="utf-8")
    return sha256(configured.authority.read_bytes()).hexdigest()


def _initialize(configured: Fixture) -> None:
    _ = create_runtime(
        configured.config,
        port=49123,
        task_authority=configured.authority,
        task_authority_sha256=configured.digest,
    )


def _restart(configured: Fixture, digest: str) -> None:
    _ = create_runtime(
        configured.config,
        port=49123,
        task_authority=configured.authority,
        task_authority_sha256=digest,
    )


def _rows(configured: Fixture) -> tuple[list[tuple[str, str]], tuple[str, str], tuple[str, ...]]:
    with read_observation_database(_database_path(configured), configured.root) as connection:
        events = [
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                "SELECT event_id,event_type FROM ticket_events ORDER BY ingest_seq"
            ).fetchall()
        ]
        policy = connection.execute(
            "SELECT evidence_hash,policy_snapshot_id FROM project_policies"
        ).fetchone()
        project = connection.execute(
            "SELECT label,logical_root_key,repo_key,identity_source,identity_source_hash "
            "FROM projects"
        ).fetchone()
    assert policy is not None
    assert project is not None
    return events, (str(policy[0]), str(policy[1])), tuple(str(value) for value in project)


def test_explicit_policy_evidence_renewal_preserves_history_and_updates_policy(
    tmp_path: Path,
) -> None:
    # Given: an existing database and a newly pinned policy declaration with exact previous pins.
    configured = fixture(tmp_path)
    _initialize(configured)
    before_events, before_policy, before_project = _rows(configured)
    digest = _renewed_authority(configured, RenewalPins(*before_policy))

    # When: the real runtime bootstrap receives the explicitly approved renewal.
    _restart(configured, digest)

    # Then: old evidence remains immutable and one new canonical pair records the current policy.
    events, policy, project = _rows(configured)
    assert events[:2] == before_events
    assert [event_type for _event_id, event_type in events] == [
        "PROJECT_IDENTITY_RESOLVED",
        "PROJECT_POLICY_RESOLVED",
        "PROJECT_IDENTITY_RESOLVED",
        "PROJECT_POLICY_RESOLVED",
    ]
    assert policy[0] == digest
    assert policy != before_policy
    assert project == before_project


def test_policy_evidence_renewal_retry_is_idempotent(tmp_path: Path) -> None:
    # Given: one successfully renewed policy and its canonical event pair.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, _existing_pins(configured))
    _restart(configured, digest)
    after_first = _rows(configured)

    # When: startup retries the exact same approved declaration.
    _restart(configured, digest)

    # Then: no policy, project, or event history changes on the retry.
    assert _rows(configured) == after_first


def test_matching_existing_policy_without_canonical_events_appends_history(
    tmp_path: Path,
) -> None:
    # Given: an existing matching project and policy whose canonical bootstrap events are absent.
    configured = fixture(tmp_path)
    _initialize(configured)
    database = Database(DatabaseConfig(_database_path(configured)))
    with database.transaction() as connection:
        _ = connection.execute("DROP TRIGGER ticket_events_no_delete")
        _ = connection.execute("DELETE FROM ingest_receipts")
        _ = connection.execute("DELETE FROM ticket_events")

    # When: startup evaluates the unchanged approved declaration.
    _restart(configured, configured.digest)

    # Then: it appends the canonical history without inserting the existing policy again.
    events, policy, _project = _rows(configured)
    assert len(events) == 2
    assert policy[0] == configured.digest


def test_changed_policy_without_explicit_renewal_is_rejected(tmp_path: Path) -> None:
    # Given: a policy declaration changed without the explicit previous-policy pins.
    configured = fixture(tmp_path)
    _initialize(configured)
    before = _rows(configured)
    digest = _renewed_authority(configured, None)

    # When: startup evaluates the changed declaration.
    with pytest.raises(RuntimeAuthorityError, match="BOOTSTRAP_EXISTING_STATE_MISMATCH"):
        _restart(configured, digest)

    # Then: the existing database remains unchanged.
    assert _rows(configured) == before


@pytest.mark.parametrize("stale_field", ["evidence_hash", "snapshot"])
def test_stale_previous_policy_pin_is_rejected(tmp_path: Path, stale_field: str) -> None:
    # Given: a renewal declaration with one stale previous-policy pin.
    configured = fixture(tmp_path)
    _initialize(configured)
    pins = _existing_pins(configured)
    stale = RenewalPins(
        "0" * 64 if stale_field == "evidence_hash" else pins.previous_evidence_hash,
        "pol_" + "0" * 24 if stale_field == "snapshot" else pins.previous_policy_snapshot_id,
    )
    digest = _renewed_authority(configured, stale)
    before = _rows(configured)

    # When: startup compares the pins to the exact current policy row.
    with pytest.raises(
        RuntimeAuthorityError,
        match="BOOTSTRAP_POLICY_RENEWAL_PREVIOUS_MISMATCH",
    ):
        _restart(configured, digest)

    # Then: stale authority cannot append or update state.
    assert _rows(configured) == before


def test_policy_renewal_rejects_changed_registered_identity(tmp_path: Path) -> None:
    # Given: an exact renewal request but a registered project identity that no longer matches.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, _existing_pins(configured))
    database = Database(DatabaseConfig(_database_path(configured)))
    with database.transaction() as connection:
        _ = connection.execute("UPDATE projects SET label='Changed identity'")
    before = _rows(configured)

    # When: startup evaluates the policy renewal against that identity.
    with pytest.raises(
        RuntimeAuthorityError,
        match="BOOTSTRAP_POLICY_RENEWAL_IDENTITY_MISMATCH",
    ):
        _restart(configured, digest)

    # Then: startup neither repairs nor further alters the registered identity.
    assert _rows(configured) == before


def test_policy_renewal_rejects_changed_permission_ceiling(tmp_path: Path) -> None:
    # Given: an exact renewal request but a stored policy with a broader authority ceiling.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, _existing_pins(configured))
    database = Database(DatabaseConfig(_database_path(configured)))
    with database.transaction() as connection:
        _ = connection.execute("UPDATE project_policies SET authority_ceiling='COMMIT'")
    before = _rows(configured)

    # When: startup compares effective Wiki, Git, and ceiling fields.
    with pytest.raises(
        RuntimeAuthorityError,
        match="BOOTSTRAP_POLICY_RENEWAL_PERMISSION_CHANGE",
    ):
        _restart(configured, digest)

    # Then: policy evidence renewal cannot normalize a permission change.
    assert _rows(configured) == before


def test_policy_renewal_fails_closed_for_active_review(tmp_path: Path) -> None:
    # Given: an exact renewal request and a project ticket currently in review.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, _existing_pins(configured))
    database = Database(DatabaseConfig(_database_path(configured)))
    with database.transaction() as connection:
        sequence = next_ingest_sequence(connection)
        now = datetime.now(UTC).isoformat()
        _ = connection.execute(
            """INSERT INTO tickets VALUES
            ('tkt_policy_review','prj_synthetic_bootstrap','Policy review','WORK_TICKET',
            'IN_REVIEW',0,'Synthetic','Renew policy',?,?,?,?,?,1)""",
            (now, now, sequence, None, None),
        )
    before = _rows(configured)

    # When: startup reaches the explicit review-state boundary.
    with pytest.raises(
        RuntimeAuthorityError,
        match="BOOTSTRAP_POLICY_RENEWAL_REVIEW_ACTIVE",
    ):
        _restart(configured, digest)

    # Then: the review and policy history remain untouched by renewal.
    assert _rows(configured) == before


def test_preflight_reports_old_database_mismatch_without_writes(tmp_path: Path) -> None:
    # Given: the old database and changed policy pins without renewal approval.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, None)
    database_path = _database_path(configured)
    before_bytes = database_path.read_bytes()
    before_rows = _rows(configured)

    # When: the public preflight inspects current authority and the existing database.
    result = preflight_runtime(configured.config, configured.authority, digest)

    # Then: it predicts startup's fixed error and leaves bytes and rows unchanged.
    assert result.status == "BLOCKED"
    assert result.code == "BOOTSTRAP_EXISTING_STATE_MISMATCH"
    assert result.action is None
    assert result.project_id is None
    assert database_path.read_bytes() == before_bytes
    assert _rows(configured) == before_rows


def test_preflight_reports_exact_renewal_ready_without_writes(tmp_path: Path) -> None:
    # Given: the old database and a changed declaration with exact renewal pins.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, _existing_pins(configured))
    database_path = _database_path(configured)
    before_bytes = database_path.read_bytes()
    before_rows = _rows(configured)

    # When: the public preflight evaluates the same decision used by startup.
    result = preflight_runtime(configured.config, configured.authority, digest)

    # Then: it reports the renewal action without opening a writable database.
    assert result.status == "READY"
    assert result.code == "RUNTIME_BOOTSTRAP_READY"
    assert result.action is RuntimeBootstrapAction.POLICY_EVIDENCE_RENEWAL
    assert result.project_id == "prj_synthetic_bootstrap"
    assert database_path.read_bytes() == before_bytes
    assert _rows(configured) == before_rows


def test_policy_renewal_rolls_back_policy_and_first_event_on_second_event_failure(
    tmp_path: Path,
) -> None:
    # Given: a valid renewal and a synthetic database trigger rejecting the second new event.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, _existing_pins(configured))
    database = Database(DatabaseConfig(_database_path(configured)))
    with database.transaction() as connection:
        _ = connection.execute(
            """CREATE TRIGGER reject_renewed_policy_event BEFORE INSERT ON ticket_events
            WHEN NEW.event_type='PROJECT_POLICY_RESOLVED'
            AND (SELECT COUNT(*) FROM ticket_events
            WHERE event_type='PROJECT_POLICY_RESOLVED') > 0
            BEGIN SELECT RAISE(ABORT,'SYNTHETIC_POLICY_EVENT_FAILURE'); END"""
        )
    before = _rows(configured)

    # When: bootstrap fails after appending identity and updating the policy in its transaction.
    with pytest.raises(sqlite3.IntegrityError, match="SYNTHETIC_POLICY_EVENT_FAILURE"):
        _restart(configured, digest)

    # Then: the transaction removes both the first event and policy update.
    assert _rows(configured) == before


def test_preflight_cli_emits_one_redacted_machine_result(tmp_path: Path) -> None:
    # Given: an exact renewal ready for a read-only CLI preflight.
    configured = fixture(tmp_path)
    _initialize(configured)
    digest = _renewed_authority(configured, _existing_pins(configured))
    environment = os.environ.copy()

    # When: an operator invokes the actual module entrypoint.
    completed = subprocess.run(  # noqa: S603 -- fixed local interpreter and module.
        [
            sys.executable,
            "-m",
            "codex_ticket_dashboard.compliance.runtime_preflight",
            "--config",
            str(configured.config),
            "--task-authority",
            str(configured.authority),
            "--task-authority-sha256",
            digest,
        ],
        capture_output=True,
        check=False,
        text=True,
        env=environment,
    )

    # Then: stdout is one JSON decision and neither output stream exposes a path.
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert len(completed.stdout.splitlines()) == 1
    output = _JSON_OBJECT.validate_json(completed.stdout)
    assert output == {
        "schema_version": 1,
        "status": "READY",
        "code": "RUNTIME_BOOTSTRAP_READY",
        "action": "POLICY_EVIDENCE_RENEWAL",
        "project_id": "prj_synthetic_bootstrap",
    }
    assert str(tmp_path) not in completed.stdout
