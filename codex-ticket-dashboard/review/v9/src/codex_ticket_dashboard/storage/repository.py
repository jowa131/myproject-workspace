"""Atomic event admission and versioned projection repository."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Final, Literal, final, override

from pydantic import TypeAdapter

from codex_ticket_dashboard.domain.identifiers import (
    EventId,
    IdempotencyKey,
    PayloadDigest,
    ProjectId,
    TicketId,
    parse_project_id,
    parse_ticket_id,
)
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.models import (
    ComplianceGateSnapshot,
    EventAdmission,
    IngestIssueSnapshot,
    ProjectionChange,
    ProjectionWrite,
    ProjectSnapshot,
    ReceiptRecord,
    TicketSnapshot,
)

type ReceiptRow = tuple[str, str, str, int, str]
type ProjectRow = tuple[str, str, str, str, str, str, int, int]
type TicketRow = tuple[
    str, str, str, str, str, int, str, str, str, str, int, str | None, str | None, int
]
type StateRow = tuple[str, str, int, int]
_RECEIPT_ROW: Final[TypeAdapter[ReceiptRow | None]] = TypeAdapter(ReceiptRow | None)
_SEQUENCE_ROW: Final[TypeAdapter[tuple[int] | None]] = TypeAdapter(tuple[int] | None)
_PROJECT_ROW: Final[TypeAdapter[ProjectRow | None]] = TypeAdapter(ProjectRow | None)
_TICKET_ROW: Final[TypeAdapter[TicketRow | None]] = TypeAdapter(TicketRow | None)
_STATE_ROW: Final[TypeAdapter[StateRow | None]] = TypeAdapter(StateRow | None)


@dataclass(frozen=True, slots=True)
class IdempotencyPayloadCollisionError(RuntimeError):
    """Reject reuse of an idempotency key for different canonical content."""

    code: Literal["IDEMPOTENCY_PAYLOAD_COLLISION"] = "IDEMPOTENCY_PAYLOAD_COLLISION"

    @override
    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, slots=True)
class SnapshotUnavailableError(LookupError):
    """Report a missing projection version at a requested watermark."""

    entity_type: str
    code: Literal["SNAPSHOT_UNAVAILABLE"] = "SNAPSHOT_UNAVAILABLE"

    @override
    def __str__(self) -> str:
        return f"{self.code}: entity={self.entity_type}"


@dataclass(frozen=True, slots=True)
class IngestSequenceUnavailableError(RuntimeError):
    """Fail closed when the singleton sequence state is missing."""

    code: Literal["INGEST_SEQUENCE_UNAVAILABLE"] = "INGEST_SEQUENCE_UNAVAILABLE"

    @override
    def __str__(self) -> str:
        return self.code


@final
class ProjectionRepository:
    """Persist admitted metadata with current and as-of projections atomically."""

    def __init__(self, database: Database) -> None:
        """Bind repository operations to one database configuration."""
        self._database = database

    def apply(self, admission: EventAdmission, change: ProjectionChange) -> ReceiptRecord:
        """Apply one persisted event and one projection mutation exactly once."""
        admission = EventAdmission.model_validate(admission)
        with self._database.transaction() as connection:
            existing = _RECEIPT_ROW.validate_python(
                connection.execute(
                    """SELECT event_id,idempotency_key,payload_digest,ingest_seq,state
                    FROM ingest_receipts WHERE idempotency_key = ?""",
                    (admission.idempotency_key,),
                ).fetchone()
            )
            if existing is not None:
                if str(existing[2]) != admission.payload_digest:
                    raise IdempotencyPayloadCollisionError
                return _receipt(existing)
            sequence_row = _SEQUENCE_ROW.validate_python(
                connection.execute(
                    """UPDATE ingest_sequences SET last_seq = last_seq + 1 WHERE singleton = 1
                    RETURNING last_seq"""
                ).fetchone()
            )
            if sequence_row is None:
                raise IngestSequenceUnavailableError
            ingest_seq = int(sequence_row[0])
            dependencies_json = json.dumps(admission.depends_on_event_ids, separators=(",", ":"))
            payload_json = json.dumps(
                admission.payload.root,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            _ = connection.execute(
                """INSERT INTO ticket_events(
                event_id,idempotency_key,payload_digest,event_type,schema_version,occurred_at,
                received_at,actor_type,origin,authority,project_observation_id,project_id,
                project_resolution_state,repo_key,session_id,turn_id,ticket_id,work_item_id,
                causation_event_id,depends_on_event_ids_json,payload_json,ingest_seq
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    admission.event_id,
                    admission.idempotency_key,
                    admission.payload_digest,
                    admission.event_type,
                    admission.schema_version,
                    admission.occurred_at.isoformat(),
                    None if admission.received_at is None else admission.received_at.isoformat(),
                    admission.actor_type.value,
                    admission.origin.value,
                    admission.authority.value,
                    admission.project_observation_id,
                    admission.project_id,
                    admission.project_resolution_state.value,
                    admission.repo_key,
                    admission.session_id,
                    admission.turn_id,
                    admission.ticket_id,
                    admission.work_item_id,
                    admission.causation_event_id,
                    dependencies_json,
                    payload_json,
                    ingest_seq,
                ),
            )
            self._database.write_projection(
                connection,
                ProjectionWrite(
                    ingest_seq=ingest_seq,
                    occurred_at=admission.occurred_at,
                    change=change,
                ),
            )
            _ = connection.execute(
                """INSERT INTO ingest_receipts(
                idempotency_key,event_id,payload_digest,state,ingest_seq,archive_state,
                archive_payload_sha256
                ) VALUES (?,?,?,?,?,'PENDING',?)""",
                (
                    admission.idempotency_key,
                    admission.event_id,
                    admission.payload_digest,
                    "APPLIED",
                    ingest_seq,
                    admission.payload_digest.removeprefix("sha256:"),
                ),
            )
            return ReceiptRecord(
                event_id=admission.event_id,
                idempotency_key=admission.idempotency_key,
                payload_digest=admission.payload_digest,
                ingest_seq=ingest_seq,
            )

    def project_as_of(self, project_id: str, watermark: int) -> ProjectSnapshot:
        """Load the exact project version visible at a watermark."""
        with self._database.read_transaction() as connection:
            row = _PROJECT_ROW.validate_python(
                connection.execute(
                    """SELECT project_id,label,logical_root_key,repo_key,identity_source,
                    identity_source_hash,created_seq,version FROM project_versions
                    WHERE project_id=? AND valid_from_ingest_seq<=?
                    AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)""",
                    (parse_project_id(project_id), watermark, watermark),
                ).fetchone()
            )
        if row is None:
            raise SnapshotUnavailableError(entity_type="project")
        return ProjectSnapshot(
            project_id=ProjectId(str(row[0])),
            label=str(row[1]),
            logical_root_key=str(row[2]),
            repo_key=str(row[3]),
            identity_source=str(row[4]),
            identity_source_hash=str(row[5]),
            created_seq=int(row[6]),
            version=int(row[7]),
        )

    def ticket_as_of(self, ticket_id: str, watermark: int) -> TicketSnapshot:
        """Load the exact ticket version visible at a watermark."""
        with self._database.read_transaction() as connection:
            row = _TICKET_ROW.validate_python(
                connection.execute(
                    """SELECT ticket_id,project_id,title,record_type,status,needs_triage,summary,
                    next_step,created_at,updated_at,created_seq,closed_at,closed_reason,version
                    FROM ticket_versions WHERE ticket_id=? AND valid_from_ingest_seq<=?
                    AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)""",
                    (parse_ticket_id(ticket_id), watermark, watermark),
                ).fetchone()
            )
        if row is None:
            raise SnapshotUnavailableError(entity_type="ticket")
        return TicketSnapshot(
            ticket_id=TicketId(str(row[0])),
            project_id=ProjectId(str(row[1])),
            title=str(row[2]),
            record_type=str(row[3]),
            status=str(row[4]),
            needs_triage=bool(row[5]),
            summary=str(row[6]),
            next_step=str(row[7]),
            created_at=datetime.fromisoformat(str(row[8])),
            updated_at=datetime.fromisoformat(str(row[9])),
            created_seq=int(row[10]),
            closed_at=None if row[11] is None else datetime.fromisoformat(str(row[11])),
            closed_reason=None if row[12] is None else str(row[12]),
            version=int(row[13]),
        )

    def compliance_gate_as_of(self, gate_id: str, watermark: int) -> ComplianceGateSnapshot:
        """Load the exact compliance gate version visible at a watermark."""
        with self._database.read_transaction() as connection:
            row = _STATE_ROW.validate_python(
                connection.execute(
                    """SELECT gate_id,status,created_seq,version FROM compliance_gate_versions
                    WHERE gate_id=? AND valid_from_ingest_seq<=?
                    AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)""",
                    (gate_id, watermark, watermark),
                ).fetchone()
            )
        if row is None:
            raise SnapshotUnavailableError(entity_type="compliance_gate")
        return ComplianceGateSnapshot(
            gate_id=str(row[0]), status=str(row[1]), created_seq=int(row[2]), version=int(row[3])
        )

    def ingest_issue_as_of(self, issue_id: str, watermark: int) -> IngestIssueSnapshot:
        """Load the exact ingest issue version visible at a watermark."""
        with self._database.read_transaction() as connection:
            row = _STATE_ROW.validate_python(
                connection.execute(
                    """SELECT issue_id,state,created_seq,version FROM ingest_issue_versions
                    WHERE issue_id=? AND valid_from_ingest_seq<=?
                    AND (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq>?)""",
                    (issue_id, watermark, watermark),
                ).fetchone()
            )
        if row is None:
            raise SnapshotUnavailableError(entity_type="ingest_issue")
        return IngestIssueSnapshot(
            issue_id=str(row[0]), state=str(row[1]), created_seq=int(row[2]), version=int(row[3])
        )


def _receipt(row: ReceiptRow) -> ReceiptRecord:
    return ReceiptRecord(
        event_id=EventId(str(row[0])),
        idempotency_key=IdempotencyKey(str(row[1])),
        payload_digest=PayloadDigest(str(row[2])),
        ingest_seq=int(row[3]),
    )
