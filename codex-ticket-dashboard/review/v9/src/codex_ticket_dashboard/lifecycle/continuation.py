"""Immutable original-turn correction budget consumed by atomic protected publication."""

import os
from pathlib import Path
from typing import ClassVar, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, model_validator

from codex_ticket_dashboard.domain.events import ValidatedEventId
from codex_ticket_dashboard.domain.identifiers import parse_payload_digest
from codex_ticket_dashboard.lifecycle.contracts import (
    Digest,
    LogicalThreadId,
    MetadataId,
    StopRequestKind,
    stop_claim_key,
)
from codex_ticket_dashboard.lifecycle.normalization import ObservationError
from codex_ticket_dashboard.storage.locks import AdmissionLock
from codex_ticket_dashboard.storage.path_security import (
    DataRootPaths,
    apply_owner_only_acl,
    validate_secure_path,
)
from codex_ticket_dashboard.storage.win32_handles import (
    create_pinned_binary,
    pin_spool_directories,
    read_pinned_bytes,
)
from codex_ticket_dashboard.storage.win32_native import Win32HandleError


class ContinuationClaim(BaseModel):
    """Durable budget only; accepted Stop evidence must independently precede any response."""

    model_config: ClassVar[ConfigDict] = ConfigDict(
        frozen=True, extra="forbid", hide_input_in_errors=True
    )
    schema_version: Literal[1] = 1
    claim_key: Digest
    source_host: MetadataId
    thread_id: LogicalThreadId
    original_turn_id: MetadataId
    claim_event_id: ValidatedEventId
    request_kind: StopRequestKind = "TICKET_CORRECTION"
    state: Literal["CLAIMED"] = "CLAIMED"

    @model_validator(mode="after")
    def validate_key(self) -> Self:
        """An original turn owns one host-scoped immutable budget identity."""
        if self.claim_key != stop_claim_key(
            self.source_host, self.thread_id, self.original_turn_id
        ):
            raise ObservationError(code="INPUT_INVALID")
        return self


def claim_path(paths: DataRootPaths, claim_key: str) -> Path:
    """Resolve only a validated digest into the fixed existing spool directory."""
    key = parse_payload_digest(claim_key)
    return paths.spool / f"stop-{key.removeprefix('sha256:')}.claim"


def read_claim(paths: DataRootPaths, claim_key: str) -> ContinuationClaim | None:
    """Serialize protected claim reads with publication handle lifetime."""
    _ = validate_secure_path(paths.admission_lock, paths.root)
    with AdmissionLock(paths.admission_lock):
        return _read_claim(paths, claim_key)


def _read_claim(paths: DataRootPaths, claim_key: str) -> ContinuationClaim | None:
    """Read protected consumed budget metadata; never infer a claim by recency."""
    path = claim_path(paths, claim_key)
    with pin_spool_directories(paths) as pinned:
        for directory in (paths.root, paths.spool):
            _ = validate_secure_path(directory, paths.root)
        if not os.path.lexists(path):
            return None
        _ = validate_secure_path(path, paths.root)
        claim = ContinuationClaim.model_validate_json(read_pinned_bytes(path, pinned.spool))
        if claim.claim_key != claim_key:
            raise ObservationError(code="ADMISSION_UNVERIFIED")
        return claim


def consume_claim(paths: DataRootPaths, claim: ContinuationClaim) -> bool:
    """Consume at most once across independent processes."""
    _ = validate_secure_path(paths.admission_lock, paths.root)
    with AdmissionLock(paths.admission_lock):
        return consume_claim_locked(paths, claim)


def consume_claim_locked(paths: DataRootPaths, claim: ContinuationClaim) -> bool:
    """Publish one marker while the caller holds paths.admission_lock; a crash spends it."""
    destination = claim_path(paths, claim.claim_key)
    temporary = paths.tmp / (destination.name + "." + uuid4().hex + ".tmp")
    with pin_spool_directories(paths) as pinned:
        for path in (paths.root, paths.spool, paths.tmp):
            _ = validate_secure_path(path, paths.root)
        existing = _read_claim(paths, claim.claim_key)
        if existing is not None:
            if existing != claim:
                raise ObservationError(code="IDEMPOTENCY_PAYLOAD_COLLISION")
            return False
        owned_temporary = False
        try:
            with create_pinned_binary(temporary, pinned.tmp) as file:
                owned_temporary = True
                apply_owner_only_acl(temporary, directory=False)
                _ = validate_secure_path(temporary, paths.root)
                _ = file.stream.write(claim.model_dump_json().encode())
                file.stream.flush()
                os.fsync(file.stream.fileno())
                try:
                    _ = file.rename_to(pinned.spool, destination.name)
                except Win32HandleError:
                    if not os.path.lexists(destination):
                        raise
                else:
                    return True
            existing = _read_claim(paths, claim.claim_key)
            if existing != claim:
                raise ObservationError(code="ADMISSION_UNVERIFIED")
            return False
        finally:
            if owned_temporary and os.path.lexists(temporary):
                _ = validate_secure_path(temporary, paths.root)
                temporary.unlink()
