"""Pinned canonical intent receipts and bounded accepted-event lookup."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

import codex_ticket_dashboard.storage.win32_native as native
from codex_ticket_dashboard.domain.events import EventEnvelope
from codex_ticket_dashboard.lifecycle.contracts import LifecyclePayload
from codex_ticket_dashboard.lifecycle.normalization import ObservationError
from codex_ticket_dashboard.storage.locks import AdmissionLock
from codex_ticket_dashboard.storage.path_security import (
    DataRootPaths,
    apply_owner_only_acl,
    validate_secure_path,
)
from codex_ticket_dashboard.storage.win32_handles import (
    VerifiedHandle,
    create_pinned_binary,
    pin_spool_directories,
    read_pinned_bytes,
    verify_handle,
)


def receipt_path(paths: DataRootPaths, event: EventEnvelope[LifecyclePayload]) -> Path:
    """An intent receipt is not proof that SpoolWriter or collector accepted it."""
    return paths.spool / f"lifecycle-{event.idempotency_key.removeprefix('sha256:')}.admission"


def canonical_intent(
    paths: DataRootPaths,
    offered: EventEnvelope[LifecyclePayload],
) -> EventEnvelope[LifecyclePayload]:
    """Persist normalized bytes once under the existing admission lock, before publication."""
    _ = validate_secure_path(paths.admission_lock, paths.root)
    with AdmissionLock(paths.admission_lock):
        return canonical_intent_locked(paths, offered)


def read_intent_locked(
    paths: DataRootPaths,
    offered: EventEnvelope[LifecyclePayload],
) -> EventEnvelope[LifecyclePayload] | None:
    """Read only normalized intent while the caller holds paths.admission_lock."""
    destination = receipt_path(paths, offered)
    with pin_spool_directories(paths) as pinned:
        for directory in (paths.root, paths.spool):
            _ = validate_secure_path(directory, paths.root)
        if not os.path.lexists(destination):
            return None
        _ = validate_secure_path(destination, paths.root)
        return EventEnvelope[LifecyclePayload].model_validate_json(
            read_pinned_bytes(destination, pinned.spool),
        )


def canonical_intent_locked(
    paths: DataRootPaths,
    offered: EventEnvelope[LifecyclePayload],
) -> EventEnvelope[LifecyclePayload]:
    """Publish canonical bytes while the caller holds paths.admission_lock."""
    destination = receipt_path(paths, offered)
    temporary = paths.tmp / (destination.name + ".tmp")
    with pin_spool_directories(paths) as pinned:
        for path in (paths.root, paths.spool, paths.tmp):
            _ = validate_secure_path(path, paths.root)
        current = read_intent_locked(paths, offered)
        if current is not None:
            excluded = {"occurred_at", "received_at"}
            if current.model_dump(exclude=excluded) != offered.model_dump(exclude=excluded):
                raise ObservationError(code="IDEMPOTENCY_PAYLOAD_COLLISION")
            return current
        with create_pinned_binary(temporary, pinned.tmp) as file:
            apply_owner_only_acl(temporary, directory=False)
            _ = validate_secure_path(temporary, paths.root)
            _ = file.stream.write(offered.model_dump_json().encode())
            file.stream.flush()
            os.fsync(file.stream.fileno())
            _ = file.rename_to(pinned.spool, destination.name)
    return offered


@contextmanager
def _directory(path: Path) -> Generator[VerifiedHandle]:
    value = native.create_file(
        native.CREATE_FILE,
        str(path),
        native.FILE_READ_ATTRIBUTES,
        native.OPEN_EXISTING,
        native.FILE_FLAG_BACKUP_SEMANTICS | native.FILE_FLAG_OPEN_REPARSE_POINT,
    )
    if value == native.INVALID_HANDLE_VALUE:
        raise native.Win32HandleError(native.Win32HandleCode.OPEN_FAILED)
    handle = native.WinHandle(value)
    try:
        yield VerifiedHandle(handle, verify_handle(handle, path))
    finally:
        _ = native.close_native(native.CLOSE_HANDLE, handle)


def accepted_copy_exists(paths: DataRootPaths, event: EventEnvelope[LifecyclePayload]) -> bool:
    """Check only the four actual event locations; receipts alone never imply acceptance."""
    scope = event.turn_id or event.session_id
    stem = "__".join(
        (sha256(scope.encode()).hexdigest()[:24], event.event_type.value, event.event_id)
    )
    found = 0
    expected = event.model_dump_json().encode()
    for directory in (
        paths.incoming,
        paths.pending_identity,
        paths.pending_dependency,
        paths.archive,
    ):
        path = directory / (stem + ".json")
        if not os.path.lexists(path):
            continue
        _ = validate_secure_path(directory, paths.root)
        with _directory(directory) as pinned:
            _ = validate_secure_path(path, paths.root)
            if read_pinned_bytes(path, pinned) != expected:
                raise ObservationError(code="ADMISSION_UNVERIFIED")
        found += 1
    if found > 1:
        raise ObservationError(code="ADMISSION_UNVERIFIED")
    return found == 1
