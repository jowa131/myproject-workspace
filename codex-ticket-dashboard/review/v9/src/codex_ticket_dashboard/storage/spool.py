"""Crash-atomic, no-clobber event spool writer."""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, assert_never, final, override

from pydantic import BaseModel

from codex_ticket_dashboard.domain.events import EventEnvelope
from codex_ticket_dashboard.domain.identifiers import EventId, TurnId
from codex_ticket_dashboard.storage.locks import AdmissionLock
from codex_ticket_dashboard.storage.path_security import (
    DataRootPaths,
    apply_owner_only_acl,
    validate_secure_path,
)
from codex_ticket_dashboard.storage.win32_handles import (
    PinnedSpoolDirectories,
    create_pinned_binary,
    pin_spool_directories,
    read_pinned_bytes,
    verify_handle,
)
from codex_ticket_dashboard.storage.win32_native import Win32HandleCode, Win32HandleError


@final
class SpoolWriteError(OSError):
    """Stable write failure that intentionally carries no accepted event identifier."""

    code: Literal[
        "SPOOL_TMP_EXISTS",
        "SPOOL_TEMP_CREATE_FAILED",
        "SPOOL_WRITE_FAILED",
        "SPOOL_SYNC_FAILED",
        "SPOOL_REPLACE_FAILED",
    ]
    operation: str

    def __init__(
        self,
        code: Literal[
            "SPOOL_TMP_EXISTS",
            "SPOOL_TEMP_CREATE_FAILED",
            "SPOOL_WRITE_FAILED",
            "SPOOL_SYNC_FAILED",
            "SPOOL_REPLACE_FAILED",
        ],
        operation: str,
    ) -> None:
        """Create a redacted failure without an accepted identifier."""
        super().__init__(code, operation)
        self.code = code
        self.operation = operation

    @override
    def __str__(self) -> str:
        return f"{self.code}: operation={self.operation}"


@dataclass(frozen=True, slots=True)
class SpoolAccepted:
    """Receipt emitted only after a new complete final file exists."""

    code: Literal["ACCEPTED"]
    event_id: EventId
    final_path: Path
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class SpoolExisting:
    """Receipt for an already present byte-identical destination."""

    code: Literal["IDEMPOTENT_EXISTING"]
    event_id: EventId
    final_path: Path
    payload_sha256: str


@dataclass(frozen=True, slots=True)
class SpoolCollision:
    """Named refusal to overwrite an existing different destination."""

    code: Literal["IDEMPOTENCY_PAYLOAD_COLLISION"]
    final_path: Path
    existing_sha256: str
    offered_sha256: str


@dataclass(frozen=True, slots=True)
class TmpRecoveryWarning:
    """Metadata-only startup warning for a preserved temporary file."""

    code: Literal["TMP_RECOVERY_REQUIRED"]
    file_name: str


type SpoolWriteResult = SpoolAccepted | SpoolExisting | SpoolCollision


@dataclass(frozen=True, slots=True)
class _PreparedSpoolWrite:
    event_id: EventId
    payload: bytes
    payload_sha256: str
    temporary: Path
    destination: Path


def _scope_hash(turn_id: TurnId | None, session_id: str) -> str:
    match turn_id:
        case None:
            scope = session_id
        case str() as value:
            scope = value
        case unreachable:
            assert_never(unreachable)
    return hashlib.sha256(scope.encode("utf-8")).hexdigest()[:24]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _require_current_pins(pinned: PinnedSpoolDirectories) -> None:
    try:
        for handle in (pinned.root, pinned.spool, pinned.tmp, pinned.incoming):
            _ = verify_handle(handle.value, handle.final_path)
    except Win32HandleError as error:
        raise SpoolWriteError(
            code="SPOOL_TEMP_CREATE_FAILED",
            operation="pin",
        ) from error


@final
class SpoolWriter:
    """Append validated event envelopes with atomic visibility and no overwrite."""

    def __init__(self, paths: DataRootPaths) -> None:
        """Bind writes to one initialized protected data root."""
        self._paths: DataRootPaths = paths

    def write[PayloadT: BaseModel](
        self,
        envelope: EventEnvelope[PayloadT],
    ) -> SpoolWriteResult:
        """Persist one already-validated envelope and return only a final outcome."""
        with pin_spool_directories(self._paths) as pinned:
            return self._commit(self._prepare(envelope), pinned)

    def _prepare[PayloadT: BaseModel](
        self,
        envelope: EventEnvelope[PayloadT],
    ) -> _PreparedSpoolWrite:
        payload = envelope.model_dump_json().encode("utf-8")
        payload_sha256 = _sha256(payload)
        stem = "__".join(
            (
                _scope_hash(envelope.turn_id, envelope.session_id),
                envelope.event_type.value,
                envelope.event_id,
            )
        )
        temporary = self._paths.tmp / f"{stem}.json.tmp"
        destination = self._paths.incoming / f"{stem}.json"
        _ = validate_secure_path(self._paths.tmp, self._paths.root)
        _ = validate_secure_path(self._paths.incoming, self._paths.root)
        _ = validate_secure_path(self._paths.admission_lock, self._paths.root)
        return _PreparedSpoolWrite(
            event_id=envelope.event_id,
            payload=payload,
            payload_sha256=payload_sha256,
            temporary=temporary,
            destination=destination,
        )

    def _commit(
        self,
        prepared: _PreparedSpoolWrite,
        pinned: PinnedSpoolDirectories,
    ) -> SpoolWriteResult:
        temporary = prepared.temporary
        destination = prepared.destination
        with AdmissionLock(self._paths.admission_lock):
            _require_current_pins(pinned)
            if os.path.lexists(destination):
                existing_sha256 = _sha256(read_pinned_bytes(destination, pinned.incoming))
                if existing_sha256 == prepared.payload_sha256:
                    return SpoolExisting(
                        code="IDEMPOTENT_EXISTING",
                        event_id=prepared.event_id,
                        final_path=destination,
                        payload_sha256=prepared.payload_sha256,
                    )
                return SpoolCollision(
                    code="IDEMPOTENCY_PAYLOAD_COLLISION",
                    final_path=destination,
                    existing_sha256=existing_sha256,
                    offered_sha256=prepared.payload_sha256,
                )
            if os.path.lexists(temporary):
                raise SpoolWriteError(code="SPOOL_TMP_EXISTS", operation="create")
            try:
                with create_pinned_binary(temporary, pinned.tmp) as pinned_file:
                    try:
                        apply_owner_only_acl(temporary, directory=False)
                        _ = validate_secure_path(temporary, self._paths.root)
                    except OSError as error:
                        raise SpoolWriteError(
                            code="SPOOL_TEMP_CREATE_FAILED",
                            operation="create",
                        ) from error
                    try:
                        _ = pinned_file.stream.write(prepared.payload)
                        pinned_file.stream.flush()
                        os.fsync(pinned_file.stream.fileno())
                    except OSError as error:
                        raise SpoolWriteError(
                            code="SPOOL_SYNC_FAILED",
                            operation="fsync",
                        ) from error
                    try:
                        _ = pinned_file.rename_to(pinned.incoming, destination.name)
                    except OSError as error:
                        raise SpoolWriteError(
                            code="SPOOL_REPLACE_FAILED",
                            operation="replace",
                        ) from error
            except Win32HandleError as error:
                match error.code:
                    case Win32HandleCode.FILE_EXISTS:
                        raise SpoolWriteError(
                            code="SPOOL_TMP_EXISTS",
                            operation="create",
                        ) from error
                    case (
                        Win32HandleCode.OPEN_FAILED
                        | Win32HandleCode.FINAL_PATH_FAILED
                        | Win32HandleCode.PATH_MISMATCH
                        | Win32HandleCode.REPARSE_FORBIDDEN
                        | Win32HandleCode.RENAME_FAILED
                    ):
                        raise SpoolWriteError(
                            code="SPOOL_TEMP_CREATE_FAILED",
                            operation="create",
                        ) from error
                    case unreachable:
                        assert_never(unreachable)
            return SpoolAccepted(
                code="ACCEPTED",
                event_id=prepared.event_id,
                final_path=destination,
                payload_sha256=prepared.payload_sha256,
            )


def scan_tmp_recovery(paths: DataRootPaths) -> tuple[TmpRecoveryWarning, ...]:
    """Report preserved interrupted temporaries without reading or deleting them."""
    _ = validate_secure_path(paths.tmp, paths.root)
    return tuple(
        TmpRecoveryWarning(code="TMP_RECOVERY_REQUIRED", file_name=path.name)
        for path in sorted(paths.tmp.iterdir(), key=lambda item: item.name)
        if path.is_file()
    )
