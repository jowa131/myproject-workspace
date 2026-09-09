import errno
import multiprocessing
import os
from pathlib import Path
from threading import Timer
from time import monotonic
from typing import Protocol

import pytest

from codex_ticket_dashboard.storage import locks


class Signal(Protocol):
    def set(self) -> None: ...
    def wait(self, timeout: float) -> bool: ...


def _hold_lock(path: str, ready: Signal, release: Signal) -> None:
    with locks.AdmissionLock(Path(path)):
        ready.set()
        assert release.wait(5)


def test_deadline_is_fixed_and_no_attempt_occurs_after_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: deterministic contention, including an overscheduled final sleep.
    path = tmp_path / "lock"
    path.write_bytes(b"0")
    for overshoot in (0.0, 0.003):
        clock = [0.0]
        attempts: list[tuple[float, int]] = []
        sleeps: list[float] = []
        descriptors: list[int] = []

        def denied(fd: int, mode: int, count: int) -> None:
            attempts.append((clock[0], mode))
            descriptors.append(fd)
            assert count == 1
            raise OSError(errno.EACCES, "synthetic contention")

        def advance(delay: float) -> None:
            assert 0 < delay <= min(0.01, 0.25 - clock[0])
            sleeps.append(delay)
            clock[0] += delay + overshoot

        with monkeypatch.context() as scoped:
            scoped.setattr(locks, "monotonic", lambda: clock[0], raising=False)
            scoped.setattr(locks, "sleep", advance, raising=False)
            scoped.setattr(locks.msvcrt, "locking", denied)
            # When / Then: never enter the critical section, preserve error and close.
            lock = locks.AdmissionLock(path)
            with pytest.raises(locks.AdmissionLockError) as caught, lock:
                pytest.fail("entered while another owner held the lock")
            assert str(caught.value) == "ADMISSION_LOCK_FAILED"
            assert lock._file is None
            with pytest.raises(OSError):
                os.fstat(descriptors[0])
            assert attempts[0] == (0.0, locks.msvcrt.LK_NBLCK)
            assert all(at < 0.25 for at, _ in attempts)
            assert sleeps and clock[0] >= 0.25


def test_uncontended_and_noncontention_errors_never_sleep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: one successful acquisition, then a non-contention error.
    path = tmp_path / "lock"
    path.write_bytes(b"0")
    calls: list[int] = []

    def forbidden_sleep(_delay: float) -> None:
        pytest.fail("unexpected sleep")

    def succeeds(_fd: int, mode: int, _count: int) -> None:
        calls.append(mode)

    monkeypatch.setattr(locks, "sleep", forbidden_sleep, raising=False)
    monkeypatch.setattr(locks.msvcrt, "locking", succeeds)
    # When / Then
    with locks.AdmissionLock(path):
        assert calls == [locks.msvcrt.LK_NBLCK]
    assert calls == [locks.msvcrt.LK_NBLCK, locks.msvcrt.LK_UNLCK]
    calls.clear()

    def invalid(_fd: int, mode: int, _count: int) -> None:
        calls.append(mode)
        raise OSError(errno.EBADF, "synthetic invalid descriptor")

    monkeypatch.setattr(locks.msvcrt, "locking", invalid)
    lock = locks.AdmissionLock(path)
    with pytest.raises(locks.AdmissionLockError) as caught, lock:
        pytest.fail("entered despite invalid descriptor")
    assert calls == [locks.msvcrt.LK_NBLCK]
    assert isinstance(caught.value.__cause__, OSError)
    assert caught.value.__cause__.errno == errno.EBADF
    assert lock._file is None


def test_independent_owner_timeout_and_short_release(tmp_path: Path) -> None:
    # Given: a separate real Windows process owns the same byte range.
    path = tmp_path / "lock"
    path.write_bytes(b"0")
    context = multiprocessing.get_context("spawn")
    ready, release = context.Event(), context.Event()
    owner = context.Process(target=_hold_lock, args=(str(path), ready, release))
    owner.start()
    timer: Timer | None = None
    try:
        assert ready.wait(5)
        lock = locks.AdmissionLock(path)
        started = monotonic()
        # When / Then: long contention fails closed and releases its handle.
        with pytest.raises(locks.AdmissionLockError), lock:
            pytest.fail("entered before owner released")
        assert 0.24 <= monotonic() - started < 1
        assert lock._file is None
        # When / Then: the same owner releases within a fresh acquisition budget.
        timer = Timer(0.04, release.set)
        timer.start()
        with locks.AdmissionLock(path) as acquired:
            assert acquired._file is not None
        assert acquired._file is None
    finally:
        release.set()
        if timer is not None:
            timer.cancel()
            timer.join(1)
        owner.join(5)
        if owner.is_alive():
            owner.terminate()
            owner.join(1)
    assert owner.exitcode == 0
