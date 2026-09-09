import multiprocessing
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, assert_never

import pytest

from codex_ticket_dashboard.domain import events, identifiers
from codex_ticket_dashboard.storage import path_security, spool
from codex_ticket_dashboard.storage.locks import AdmissionLock


class ProcessEvent(Protocol):
    def set(self) -> None: ...

    def wait(self, timeout: float | None = None) -> bool: ...


@dataclass(frozen=True, slots=True)
class ChildWriteSpec:
    root: str
    event_json: str
    result_path: str
    lock_acquired: ProcessEvent
    release_lock: ProcessEvent
    writer_prepared: ProcessEvent
    writer_done: ProcessEvent
    coordinate_lock: bool
def _write_in_child(spec: ChildWriteSpec) -> None:
    paths = path_security.data_root_paths(Path(spec.root))
    event = events.EventEnvelope[events.EmptyPayload].model_validate_json(spec.event_json)
    if spec.coordinate_lock:
        with AdmissionLock(paths.admission_lock):
            spec.lock_acquired.set()
            assert spec.release_lock.wait(5.0)
    else:
        assert spec.lock_acquired.wait(5.0)

    def observed_admission_lock(path: Path) -> AdmissionLock:
        spec.writer_prepared.set()
        return AdmissionLock(path)

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "codex_ticket_dashboard.storage.spool.AdmissionLock",
            observed_admission_lock,
        )
        result = spool.SpoolWriter(paths).write(event)
    match result:
        case spool.SpoolAccepted(code=code, payload_sha256=digest):
            rendered = f"{code}|{digest}"
        case spool.SpoolExisting(code=code, payload_sha256=digest):
            rendered = f"{code}|{digest}"
        case spool.SpoolCollision(code=code, offered_sha256=digest):
            rendered = f"{code}|{digest}"
        case unreachable:
            assert_never(unreachable)
    _ = Path(spec.result_path).write_text(rendered, encoding="utf-8")
    spec.writer_done.set()


def _event(
    event_id: identifiers.EventId | None = None,
    digest_char: str = "b",
) -> events.EventEnvelope[events.EmptyPayload]:
    return events.EventEnvelope[events.EmptyPayload](
        schema_version=1,
        event_id=event_id or identifiers.new_event_id(),
        event_type=events.EventType.THREAD_OBSERVED,
        occurred_at=datetime(2026, 9, 5, 12, tzinfo=UTC),
        received_at=None,
        actor_type=events.ActorType.OBSERVER,
        origin=events.EventOrigin.MCP_TOOL,
        project_observation_id=identifiers.new_project_observation_id(),
        project_id=identifiers.ProjectId("prj_synthetic_dashboard"),
        project_resolution_state=events.ProjectResolutionState.RESOLVED,
        repo_key=identifiers.RepoKey("repo_synthetic_repository"),
        session_id=identifiers.SessionId("thr_synthetic"),
        turn_id=identifiers.TurnId("turn_synthetic"),
        ticket_id=None,
        work_item_id=None,
        causation_event_id=None,
        depends_on_event_ids=(),
        payload=events.EmptyPayload(),
        idempotency_key=identifiers.IdempotencyKey(f"sha256:{'a' * 64}"),
        payload_digest=identifiers.PayloadDigest(f"sha256:{digest_char * 64}"),
    )




@pytest.mark.parametrize(
    ("second_digest", "expected_codes"),
    [
        ("b", {"ACCEPTED", "IDEMPOTENT_EXISTING"}),
        ("c", {"ACCEPTED", "IDEMPOTENCY_PAYLOAD_COLLISION"}),
    ],
)
def test_cross_process_lock_makes_same_event_no_clobber_deterministic(
    tmp_path: Path,
    second_digest: str,
    expected_codes: set[str],
) -> None:
    # Given: two spawned writers coordinated while one holds the real admission lock.
    paths = path_security.initialize_data_root(tmp_path / "dashboard-root")
    first_event = _event()
    second_event = first_event.model_copy(
        update={"payload_digest": identifiers.PayloadDigest(f"sha256:{second_digest * 64}")}
    )
    context = multiprocessing.get_context("spawn")
    lock_acquired = context.Event()
    release_lock = context.Event()
    first_prepared = context.Event()
    second_prepared = context.Event()
    first_done = context.Event()
    second_done = context.Event()
    first_result = tmp_path / "first.result"
    second_result = tmp_path / "second.result"
    first_spec = ChildWriteSpec(
        root=str(paths.root),
        event_json=first_event.model_dump_json(),
        result_path=str(first_result),
        lock_acquired=lock_acquired,
        release_lock=release_lock,
        writer_prepared=first_prepared,
        writer_done=first_done,
        coordinate_lock=True,
    )
    second_spec = ChildWriteSpec(
        root=str(paths.root),
        event_json=second_event.model_dump_json(),
        result_path=str(second_result),
        lock_acquired=lock_acquired,
        release_lock=release_lock,
        writer_prepared=second_prepared,
        writer_done=second_done,
        coordinate_lock=False,
    )
    first_process = context.Process(target=_write_in_child, args=(first_spec,))
    second_process = context.Process(target=_write_in_child, args=(second_spec,))

    # When: the second writer reaches admission while the first owns the lock.
    lock_blocked_second_writer = False
    try:
        first_process.start()
        assert lock_acquired.wait(5.0)
        second_process.start()
        assert second_prepared.wait(5.0)
        lock_blocked_second_writer = not second_done.wait(0.03)
    finally:
        release_lock.set()
        for process in (first_process, second_process):
            if process.pid is None:
                continue
            process.join(5.0)
            if process.is_alive():
                process.terminate()
                process.join(1.0)

    # Then: both exit, exactly one final is complete, and outcomes are named.
    assert lock_blocked_second_writer is True
    assert first_process.exitcode == 0
    assert second_process.exitcode == 0
    assert first_done.is_set()
    assert second_done.is_set()
    codes = {
        first_result.read_text(encoding="utf-8").split("|", maxsplit=1)[0],
        second_result.read_text(encoding="utf-8").split("|", maxsplit=1)[0],
    }
    assert codes == expected_codes
    finals = tuple(paths.incoming.glob("*.json"))
    assert len(finals) == 1
    assert finals[0].read_bytes() in {
        first_event.model_dump_json().encode("utf-8"),
        second_event.model_dump_json().encode("utf-8"),
    }
    assert tuple(paths.tmp.iterdir()) == ()

