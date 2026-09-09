import json
import os
import subprocess
import sys
from pathlib import Path
from time import perf_counter

import pytest
from pydantic import TypeAdapter
from tests.integration.stop_fixture import StopFixture, stop_fixture

from codex_ticket_dashboard.domain.events import EventEnvelope
from codex_ticket_dashboard.lifecycle.command import observe
from codex_ticket_dashboard.lifecycle.continuation import read_claim
from codex_ticket_dashboard.lifecycle.contracts import LifecyclePayload, stop_claim_key
from codex_ticket_dashboard.mcp.official_context import ContextResolver, parse_official_metadata
from codex_ticket_dashboard.mcp.schemas import TicketTurnSummaryRequest
from codex_ticket_dashboard.mcp.tools import EventRecorder
from codex_ticket_dashboard.storage.path_security import (
    PathSecurityError,
    apply_owner_only_acl,
    inspect_owner_only_acl,
)
from codex_ticket_dashboard.storage.spool import SpoolWriter
def _stop_args(fixture: StopFixture) -> list[str]:
    return [
        sys.executable,
        "-m",
        "codex_ticket_dashboard.lifecycle.command",
        "--config",
        str(fixture.config),
        "--source-host",
        "host_synthetic",
        "--source-kind",
        "cli",
    ]


def test_stop_full_process_race_outputs_at_most_one_correction(tmp_path: Path) -> None:
    fixture = stop_fixture(tmp_path)
    processes = [
        subprocess.Popen(  # noqa: S603
            _stop_args(fixture),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for _ in range(2)
    ]
    try:
        for process in processes:
            assert process.stdin is not None
            _ = process.stdin.write(fixture.raw)
            process.stdin.close()
            process.stdin = None
        results = [process.communicate(timeout=5) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=1)
    assert sum(bool(stdout) for stdout, _stderr in results) == 1
    assert all(stderr == b"" for _stdout, stderr in results)
    assert all(process.returncode == 0 for process in processes)
    assert len(tuple(fixture.paths.incoming.glob("*TURN_STOPPED*.json"))) == 1


def test_stop_publication_failure_after_claim_never_requests_on_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = stop_fixture(tmp_path)

    def fail_publication(*_args: object, **_kwargs: object) -> None:
        message = "PRIVATE_EXCEPTION_CANARY"
        raise OSError(message)

    with monkeypatch.context() as scoped:
        scoped.setattr(SpoolWriter, "write", fail_publication)
        with pytest.raises(OSError, match="PRIVATE_EXCEPTION_CANARY"):
            _ = observe(fixture.raw, fixture.config, "host_synthetic", "cli")
    assert len(tuple(fixture.paths.spool.glob("stop-*.claim"))) == 1
    assert len(tuple(fixture.paths.incoming.glob("*TURN_STOPPED*.json"))) == 0
    assert observe(fixture.raw, fixture.config, "host_synthetic", "cli") is None
    assert len(tuple(fixture.paths.incoming.glob("*TURN_STOPPED*.json"))) == 1

