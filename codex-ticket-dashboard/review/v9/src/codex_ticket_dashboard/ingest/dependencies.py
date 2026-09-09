"""Deterministic dependency admission and terminal propagation."""

import sqlite3
from collections import deque
from dataclasses import dataclass
from typing import Final, Literal, assert_never

from pydantic import TypeAdapter

from codex_ticket_dashboard.domain.identifiers import EventId, IdempotencyKey, PayloadDigest
from codex_ticket_dashboard.storage.database import Database

type ReceiptStateRow = tuple[str, str | None, str | None]
type EdgeRow = tuple[str, str]
type EventRow = tuple[str]
type SequenceRow = tuple[int | None]
_RECEIPT_STATE: Final[TypeAdapter[ReceiptStateRow | None]] = TypeAdapter(ReceiptStateRow | None)
_EDGES: Final[TypeAdapter[list[EdgeRow]]] = TypeAdapter(list[EdgeRow])
_EVENT_ROWS: Final[TypeAdapter[list[EventRow]]] = TypeAdapter(list[EventRow])
_SEQUENCE_ROW: Final[TypeAdapter[SequenceRow | None]] = TypeAdapter(SequenceRow | None)
_EMPTY_EXCLUSIONS: Final[frozenset[EventId]] = frozenset()


@dataclass(frozen=True, slots=True)
class DependenciesReady:
    """All declared dependency receipts are applied."""


@dataclass(frozen=True, slots=True)
class DependenciesPending:
    """At least one dependency has no applied terminal receipt yet."""

    dependency_event_ids: tuple[EventId, ...]


@dataclass(frozen=True, slots=True)
class DependencyTerminal:
    """A direct dependency is permanently rejected or dependency-failed."""

    failed_dependency_event_id: EventId
    root_failed_dependency_event_id: EventId


type DependencyAssessment = DependenciesReady | DependenciesPending | DependencyTerminal


@dataclass(frozen=True, slots=True)
class PendingEventReceipt:
    """Receipt identity needed to terminalize one newly discovered child."""

    event_id: EventId
    idempotency_key: IdempotencyKey
    payload_digest: PayloadDigest


@dataclass(frozen=True, slots=True)
class DependencyAdmission:
    """Atomic dependency-index admission outcome."""

    failed_event_ids: tuple[EventId, ...]
    deferred: bool


def assess_dependencies(
    connection: sqlite3.Connection,
    dependencies: tuple[EventId, ...],
) -> DependencyAssessment:
    """Classify dependencies from durable receipts, independent of discovery order."""
    pending: list[EventId] = []
    for event_id in sorted(set(dependencies)):
        row = _RECEIPT_STATE.validate_python(
            connection.execute(
                """SELECT state,failed_dependency_event_id,root_failed_dependency_event_id
                FROM ingest_receipts WHERE event_id=?""",
                (event_id,),
            ).fetchone()
        )
        if row is None or row[0] in {"RECEIVED", "PENDING_IDENTITY", "PENDING_DEPENDENCY"}:
            pending.append(event_id)
            continue
        if row[0] == "APPLIED":
            continue
        root = EventId(str(row[2])) if row[2] is not None else event_id
        return DependencyTerminal(event_id, root)
    return DependenciesPending(tuple(pending)) if pending else DependenciesReady()


def admit_event_dependencies(
    database: Database,
    event: PendingEventReceipt,
    dependencies: tuple[EventId, ...],
) -> DependencyAdmission:
    """Persist pending or terminal state in one dependency transaction."""
    with database.transaction() as connection:
        assessment = assess_dependencies(connection, dependencies)
        match assessment:
            case DependenciesPending():
                persist_pending(
                    connection,
                    event.event_id,
                    event.idempotency_key,
                    event.payload_digest,
                    dependencies,
                )
                failed = fail_cycle(connection, cycle_participants(connection, event.event_id))
                return DependencyAdmission(failed_event_ids=failed, deferred=not failed)
            case DependencyTerminal(failed_parent, root_failure):
                failed = fail_dependency_event(connection, event, failed_parent, root_failure)
                return DependencyAdmission(failed_event_ids=failed, deferred=False)
            case DependenciesReady():
                return DependencyAdmission(failed_event_ids=(), deferred=False)
            case unreachable:
                assert_never(unreachable)


def persist_pending(
    connection: sqlite3.Connection,
    event_id: EventId,
    idempotency_key: str,
    payload_digest: PayloadDigest,
    dependencies: tuple[EventId, ...],
) -> None:
    """Persist a dependency receipt and its reverse replay index atomically."""
    _ = connection.execute(
        """INSERT INTO ingest_receipts(idempotency_key,event_id,payload_digest,state)
        VALUES (?,?,?,'PENDING_DEPENDENCY')
        ON CONFLICT(idempotency_key) DO UPDATE SET state='PENDING_DEPENDENCY'""",
        (idempotency_key, event_id, payload_digest),
    )
    _ = connection.execute("DELETE FROM pending_dependencies WHERE event_id=?", (event_id,))
    _ = connection.executemany(
        """INSERT INTO pending_dependencies(event_id,dependency_event_id,payload_digest)
        VALUES (?,?,?)""",
        ((event_id, dependency, payload_digest) for dependency in sorted(set(dependencies))),
    )


def cycle_participants(connection: sqlite3.Connection, start: EventId) -> tuple[EventId, ...]:
    """Return the cycle closed by start using a bounded graph traversal."""
    graph: dict[EventId, tuple[EventId, ...]] = {}
    for child, parent in _EDGES.validate_python(
        connection.execute(
            "SELECT event_id,dependency_event_id FROM pending_dependencies"
        ).fetchall()
    ):
        child_id = EventId(child)
        graph[child_id] = (*graph.get(child_id, ()), EventId(parent))
    participants: set[EventId] = set()
    for dependency in graph.get(start, ()):
        path = _path_to(graph, dependency, start)
        if path is not None:
            participants.update((start, *path))
    return tuple(sorted(participants))


def fail_cycle(
    connection: sqlite3.Connection,
    participants: tuple[EventId, ...],
) -> tuple[EventId, ...]:
    """Terminalize a complete dependency cycle and its non-cycle descendants."""
    if not participants:
        return ()
    root = min(participants)
    for event_id in participants:
        _ = connection.execute(
            """UPDATE ingest_receipts SET state='DEPENDENCY_FAILED',
            failure_code='DEPENDENCY_CYCLE',failed_dependency_event_id=?,
            root_failed_dependency_event_id=? WHERE event_id=?""",
            (root, root, event_id),
        )
    for event_id in participants:
        _ = connection.execute(
            "DELETE FROM pending_dependencies WHERE event_id=?", (event_id,)
        )
    descendants: list[EventId] = []
    for event_id in participants:
        descendants.extend(
            propagate_terminal(
                connection,
                event_id,
                code="DEPENDENCY_CYCLE",
                excluded=frozenset(participants),
            )
        )
    return tuple(sorted((*participants, *set(descendants))))


def fail_dependency_event(
    connection: sqlite3.Connection,
    event: PendingEventReceipt,
    failed_parent: EventId,
    root_failure: EventId,
) -> tuple[EventId, ...]:
    """Persist a child's terminal receipt and propagate its root cause."""
    _ = connection.execute(
        """INSERT INTO ingest_receipts(
        idempotency_key,event_id,payload_digest,state,failure_code,
        failed_dependency_event_id,root_failed_dependency_event_id
        ) VALUES (?,?,?,'DEPENDENCY_FAILED','DEPENDENCY_REJECTED',?,?)
        ON CONFLICT(idempotency_key) DO UPDATE SET state='DEPENDENCY_FAILED',
        failure_code='DEPENDENCY_REJECTED',failed_dependency_event_id=excluded.failed_dependency_event_id,
        root_failed_dependency_event_id=excluded.root_failed_dependency_event_id""",
        (
            event.idempotency_key,
            event.event_id,
            event.payload_digest,
            failed_parent,
            root_failure,
        ),
    )
    descendants = propagate_terminal(connection, event.event_id, code="DEPENDENCY_REJECTED")
    return (event.event_id, *descendants)


def propagate_terminal(
    connection: sqlite3.Connection,
    root: EventId,
    *,
    code: Literal["DEPENDENCY_REJECTED", "DEPENDENCY_CYCLE"],
    excluded: frozenset[EventId] = _EMPTY_EXCLUSIONS,
) -> tuple[EventId, ...]:
    """Fail descendants in deterministic depth, ingest sequence, and event-id order."""
    queue = deque([(root, 0)])
    direct_parent: dict[EventId, EventId] = {}
    depth_by_event: dict[EventId, int] = {}
    while queue:
        parent, depth = queue.popleft()
        children = tuple(
            EventId(str(row[0]))
            for row in _EVENT_ROWS.validate_python(
                connection.execute(
                """SELECT event_id FROM pending_dependencies
                WHERE dependency_event_id=? ORDER BY event_id""",
                (parent,),
                ).fetchall()
            )
        )
        for child in children:
            if child in excluded or child in depth_by_event:
                continue
            direct_parent[child] = parent
            depth_by_event[child] = depth + 1
            queue.append((child, depth + 1))
    ordered = sorted(
        depth_by_event,
        key=lambda event_id: (
            depth_by_event[event_id],
            _receipt_sequence(connection, event_id),
            event_id,
        ),
    )
    for event_id in ordered:
        _ = connection.execute(
            """UPDATE ingest_receipts SET state='DEPENDENCY_FAILED',failure_code=?,
            failed_dependency_event_id=?,root_failed_dependency_event_id=? WHERE event_id=?""",
            (code, direct_parent[event_id], root, event_id),
        )
        _ = connection.execute("DELETE FROM pending_dependencies WHERE event_id=?", (event_id,))
    return tuple(ordered)


def _path_to(
    graph: dict[EventId, tuple[EventId, ...]],
    source: EventId,
    target: EventId,
) -> tuple[EventId, ...] | None:
    stack: list[tuple[EventId, tuple[EventId, ...]]] = [(source, (source,))]
    visited: set[EventId] = set()
    while stack:
        node, path = stack.pop()
        if node == target:
            return path
        if node in visited:
            continue
        visited.add(node)
        stack.extend(
            (dependency, (*path, dependency)) for dependency in sorted(graph.get(node, ()))
        )
    return None


def _receipt_sequence(connection: sqlite3.Connection, event_id: EventId) -> int:
    row = _SEQUENCE_ROW.validate_python(
        connection.execute(
            "SELECT ingest_seq FROM ingest_receipts WHERE event_id=?", (event_id,)
        ).fetchone()
    )
    return 2**63 - 1 if row is None or row[0] is None else int(row[0])
