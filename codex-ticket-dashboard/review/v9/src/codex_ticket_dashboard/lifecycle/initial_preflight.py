"""Prove a first-record gap from applied exact observations and real pending data."""

import json
import sqlite3
from typing import Final

from pydantic import TypeAdapter

import codex_ticket_dashboard.storage.win32_native as native
from codex_ticket_dashboard.compliance.project_registry import ProjectResolution
from codex_ticket_dashboard.domain.events import ProjectResolutionState
from codex_ticket_dashboard.ingest.dead_letter import (
    SafeDocument,
    inspect_raw_json,
    parse_collected_event,
)
from codex_ticket_dashboard.ingest.recovery import read_safe_event, scan_spool
from codex_ticket_dashboard.lifecycle.continuation import ContinuationClaim
from codex_ticket_dashboard.lifecycle.contracts import (
    LIFECYCLE_EVENT_TYPES,
    LifecyclePayload,
    MetadataId,
)
from codex_ticket_dashboard.storage.path_security import DataRootPaths, validate_secure_path
from codex_ticket_dashboard.storage.turn_recording import TurnKey
from codex_ticket_dashboard.storage.win32_handles import (
    VerifiedHandle,
    pin_spool_directories,
    read_pinned_bytes,
    verify_handle,
)

_LIMIT: Final = 256
_ROWS: Final = TypeAdapter(list[tuple[str, str | None, str, str | None, str, str, str, str]])
_COUNT: Final = TypeAdapter(tuple[int])
_TURN: Final[TypeAdapter[str]] = TypeAdapter(MetadataId)


def initial_absence(
    connection: sqlite3.Connection,
    paths: DataRootPaths,
    key: TurnKey,
    identity: ProjectResolution,
) -> bool:
    """Require an applied exact UPS; legacy or conflicting business data is never absence."""
    if identity.state is not ProjectResolutionState.RESOLVED or identity.project_id is None:
        return False
    rows = _ROWS.validate_python(
        connection.execute(
            """SELECT source_host,parent_thread_id,relation_state,project_id,
        project_observation_id,project_resolution_state,hook_event,source_kind
        FROM lifecycle_observations WHERE thread_id=? AND turn_id=? LIMIT 257""",
            (key.thread_id, key.turn_id),
        ).fetchall()
    )
    if not rows or len(rows) > _LIMIT or not any(row[6] == "UserPromptSubmit" for row in rows):
        return False
    if any(
        row[0] != key.source_host
        or row[1] != key.parent_thread_id
        or row[2] == "CONFLICT"
        or row[3] != identity.project_id
        or row[4] != identity.observation_id
        or row[5] != "RESOLVED"
        or row[6] == "Stop"
        or row[7] not in {"cli", "vscode", "unknown"}
        for row in rows
    ):
        return False
    count = _COUNT.validate_python(
        connection.execute(
            """SELECT COUNT(*) FROM ticket_events WHERE session_id=?
        AND (turn_id=? OR turn_id IS NULL)""",
            (key.thread_id, key.turn_id),
        ).fetchone()
    )[0]
    return count == 0 and _pending_clear(paths, key, identity)


def _pending_clear(paths: DataRootPaths, key: TurnKey, identity: ProjectResolution) -> bool:
    for directory in (
        paths.incoming,
        paths.pending_identity,
        paths.pending_dependency,
        paths.tmp,
        paths.dead_letter,
    ):
        _ = validate_secure_path(directory, paths.root)
    if any(paths.tmp.iterdir()) or not _failed_clear(paths, key):
        return False
    candidates = tuple(scan_spool(paths))
    if len(candidates) > _LIMIT:
        return False
    for path in candidates:
        _ = validate_secure_path(path, paths.root)
        event = read_safe_event(path)
        if event is None:
            return False
        if event.session_id != key.thread_id or event.turn_id not in {None, key.turn_id}:
            continue
        if event.event_type.value not in LIFECYCLE_EVENT_TYPES:
            return False
        # Pending observations cannot establish the applied UPS, but may contradict it.
        payload = LifecyclePayload.model_validate(event.payload.root)
        if (
            payload.source_host != key.source_host
            or payload.parent_thread_id != key.parent_thread_id
            or payload.relation_state == "CONFLICT"
            or event.project_id != identity.project_id
            or event.project_observation_id != identity.observation_id
        ):
            return False
    return True


def _failed_clear(paths: DataRootPaths, key: TurnKey) -> bool:
    """Exclude only complete explicit other-turn identities read through pinned safe handles."""
    candidates = tuple(paths.dead_letter.iterdir())
    if not candidates:
        return True
    if len(candidates) > _LIMIT:
        return False
    with pin_spool_directories(paths) as pins:
        canonical = validate_secure_path(paths.dead_letter, paths.root)
        value = native.create_file(
            native.CREATE_FILE,
            str(canonical),
            native.FILE_READ_ATTRIBUTES,
            native.OPEN_EXISTING,
            native.FILE_FLAG_BACKUP_SEMANTICS | native.FILE_FLAG_OPEN_REPARSE_POINT,
        )
        if value == native.INVALID_HANDLE_VALUE:
            return False
        handle = native.WinHandle(value)
        try:
            parent = VerifiedHandle(
                handle,
                verify_handle(handle, pins.spool.final_path / "dead-letter"),
            )
            for path in candidates:
                _ = validate_secure_path(path, paths.root)
                inspected = inspect_raw_json(read_pinned_bytes(path, parent))
                if not isinstance(inspected, SafeDocument):
                    return False
                event = parse_collected_event(inspected.value)
                turn = _TURN.validate_python(event.turn_id)
                if (event.session_id, turn) == (key.thread_id, key.turn_id):
                    return False
            return set(candidates) == set(paths.dead_letter.iterdir())
        finally:
            _ = native.close_native(native.CLOSE_HANDLE, handle)


def initial_response(claim: ContinuationClaim) -> str:
    """Ask only for truthful preflight in the same official turn, without a business cause."""
    instruction = {
        "code": "CTD_INITIAL_PREFLIGHT_V1",
        "relation": "INITIAL_PREFLIGHT",
        "observation_event_id": claim.claim_event_id,
        "original_turn_id": claim.original_turn_id,
        "missing_requirements": ["PREFLIGHT"],
        "instruction": (
            "Begin with the missing truthful preflight using ticket_preflight_record in the "
            "current official turn. Preserve explicit user restrictions. After preflight resolves "
            "classification and applied policy, follow those verified requirements and the "
            "existing recording contract for any remaining truthful records. Never supply "
            "fabricated ticket IDs, results, "
            "or user decisions. "
            "Do not use this observation_event_id as context.causation_event_id. If the official "
            "turn differs, recording is unavailable, or user restrictions forbid it, finish with "
            "recording incomplete; do not infer a continuation relation or retry this request."
        ),
    }
    return json.dumps(
        {
            "decision": "block",
            "reason": json.dumps(instruction, separators=(",", ":")),
        }
    )
