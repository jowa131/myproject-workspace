"""Snapshot-bounded read-only activity API including unresolved observations."""

import json
from typing import ClassVar, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from codex_ticket_dashboard.lifecycle.contracts import (
    CoverageState,
    MissingRequirement,
    RelationState,
)
from codex_ticket_dashboard.storage.database import Database
from codex_ticket_dashboard.storage.readonly_observation import read_observation_database
from codex_ticket_dashboard.storage.recording_assessment import assess_recording
from codex_ticket_dashboard.storage.turn_recording import TurnKey


class ActivityPageRequest(BaseModel):
    """Exact metadata filters and immutable ingest-sequence pagination."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")
    limit: int = Field(default=50, ge=1, le=200)
    after_ingest_seq: int = Field(default=0, ge=0)
    snapshot_high_watermark: int | None = Field(default=None, ge=0)
    source_host: str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    parent_thread_id: str | None = None
    ticket_id: str | None = None


class Activity(BaseModel):
    """Immutable observed identity separated from effective registry resolution."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")
    event_id: str
    ingest_seq: int
    observed_at: str
    source_host: str
    source_kind: Literal["cli", "vscode", "unknown"]
    hook_event: str
    event_type: str
    thread_id: str
    turn_id: str | None
    parent_thread_id: str | None
    effective_parent_thread_id: str | None
    relation_state: RelationState
    effective_relation_state: RelationState
    project_observation_id: str
    project_id: str | None
    project_resolution_state: Literal["RESOLVED", "UNCLASSIFIED", "CONFLICT"]
    effective_project_id: str | None
    effective_project_resolution_state: Literal["RESOLVED", "UNCLASSIFIED", "CONFLICT"]
    coverage: CoverageState
    mcp_readiness: Literal["READY", "UNVERIFIED", "UNAVAILABLE"]
    missing_requirements: tuple[MissingRequirement, ...]
    effective_missing_requirements: tuple[MissingRequirement, ...]
    linked_ticket_ids: tuple[str, ...]
    semantic_state: Literal["RECORDED", "MISSING", "UNVERIFIED"]


class ActivityPage(BaseModel):
    """Fixed-membership page with the next immutable sequence or end marker."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)
    items: tuple[Activity, ...]
    snapshot_high_watermark: int
    next_after_ingest_seq: int | None


_ROWS: Final = TypeAdapter(list[tuple[str]])
_SEQUENCE: Final = TypeAdapter(tuple[int])
_MAPPING: Final = TypeAdapter(dict[str, JsonValue])
_VALUES: Final = TypeAdapter(list[tuple[JsonValue, ...]])


class LifecycleQueries:
    """Read activity without manufacturing tickets or changing observed state."""

    def __init__(self, database: Database) -> None:
        """Bind the existing database without creating or migrating storage."""
        self._database: Database = database

    def activities(self, request: ActivityPageRequest) -> ActivityPage:
        """Bound observations, links and effective identities by one snapshot."""
        with read_observation_database(
            self._database.path, self._database.path.parent
        ) as connection:
            current = _SEQUENCE.validate_python(
                connection.execute(
                    "SELECT last_seq FROM ingest_sequences WHERE singleton=1",
                ).fetchone()
            )[0]
            high = (
                current
                if request.snapshot_high_watermark is None
                else min(
                    request.snapshot_high_watermark,
                    current,
                )
            )
            rows = connection.execute(
                """WITH activity AS (SELECT o.*,
                CASE WHEN o.relation_state='CONFLICT' THEN 'CONFLICT'
                WHEN EXISTS(SELECT 1 FROM lifecycle_mcp_contexts m
                    JOIN ticket_events b ON b.event_id=m.event_id
                    WHERE m.source_host=o.source_host AND m.thread_id=o.thread_id
                    AND m.turn_id=o.turn_id AND (m.parent_thread_id IS o.parent_thread_id
                        OR (o.parent_thread_id IS NULL AND o.relation_state='UNVERIFIED'))
                    AND b.project_observation_id=o.project_observation_id AND b.ingest_seq<=?)
                THEN 'VERIFIED' ELSE 'UNVERIFIED' END AS effective_relation_state,
                COALESCE(o.parent_thread_id,(SELECT m.parent_thread_id
                    FROM lifecycle_mcp_contexts m JOIN ticket_events b ON b.event_id=m.event_id
                    WHERE m.source_host=o.source_host AND m.thread_id=o.thread_id
                    AND m.turn_id=o.turn_id AND b.ingest_seq<=?
                    AND b.project_observation_id=o.project_observation_id LIMIT 1))
                    AS effective_parent_thread_id,
                COALESCE(o.project_id,(SELECT r.resolved_project_id
                    FROM event_project_resolutions r WHERE
                    r.project_observation_id=o.project_observation_id
                    AND r.resolved_at_ingest_seq<=? LIMIT 1)) AS effective_project_id
                FROM lifecycle_observations o)
                SELECT * FROM activity o
                WHERE o.ingest_seq>? AND o.ingest_seq<=?
                    AND (? IS NULL OR o.source_host=?)
                    AND (? IS NULL OR o.thread_id=?) AND (? IS NULL OR o.turn_id=?)
                    AND (? IS NULL OR o.effective_parent_thread_id=?)
                    AND (? IS NULL OR EXISTS(SELECT 1 FROM lifecycle_activity_links l
                        WHERE l.observation_event_id=o.event_id AND l.ticket_id=?
                        AND l.linked_ingest_seq<=?))
                ORDER BY o.ingest_seq,o.event_id LIMIT ?""",
                (
                    high,
                    high,
                    high,
                    request.after_ingest_seq,
                    high,
                    request.source_host,
                    request.source_host,
                    request.thread_id,
                    request.thread_id,
                    request.turn_id,
                    request.turn_id,
                    request.parent_thread_id,
                    request.parent_thread_id,
                    request.ticket_id,
                    request.ticket_id,
                    high,
                    request.limit + 1,
                ),
            )
            columns = tuple(description[0] for description in rows.description)
            records = [
                _MAPPING.validate_python(dict(zip(columns, row, strict=True)))
                for row in _VALUES.validate_python(rows.fetchall())
            ]
            items: list[Activity] = []
            for record in records[: request.limit]:
                links = _ROWS.validate_python(
                    connection.execute(
                        """SELECT DISTINCT ticket_id FROM lifecycle_activity_links
                    WHERE observation_event_id=? AND linked_ingest_seq<=? ORDER BY ticket_id""",
                        (record["event_id"], high),
                    ).fetchall()
                )
                missing = record.pop("missing_requirements_json")
                if not isinstance(missing, str):
                    raise TypeError
                record["missing_requirements"] = json.loads(missing)
                record["effective_missing_requirements"] = record["missing_requirements"]
                record["linked_ticket_ids"] = [row[0] for row in links]
                record["effective_project_resolution_state"] = (
                    "RESOLVED"
                    if record["effective_project_id"] is not None
                    else record["project_resolution_state"]
                )
                record["semantic_state"] = (
                    "MISSING"
                    if record["missing_requirements"]
                    else "RECORDED"
                    if links
                    else "UNVERIFIED"
                )
                activity = Activity.model_validate(record)
                if activity.event_type == "TURN_STOPPED" and activity.turn_id is not None:
                    assessed = assess_recording(
                        connection,
                        TurnKey(
                            activity.source_host,
                            activity.thread_id,
                            activity.turn_id,
                            activity.effective_parent_thread_id,
                        ),
                        high,
                    )
                    activity = activity.model_copy(
                        update={
                            "effective_missing_requirements": assessed.missing_requirements,
                            "semantic_state": "RECORDED"
                            if assessed.state == "COMPLETE"
                            else "MISSING"
                            if assessed.state in {"MISSING", "BLOCKED"}
                            else "UNVERIFIED",
                        }
                    )
                items.append(activity)
            return ActivityPage(
                items=tuple(items),
                snapshot_high_watermark=high,
                next_after_ingest_seq=items[-1].ingest_seq
                if len(records) > request.limit
                else None,
            )
