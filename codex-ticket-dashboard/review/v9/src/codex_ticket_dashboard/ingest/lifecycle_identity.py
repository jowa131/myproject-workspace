"""Exact validated registry replay for already archived unresolved observations."""

from hashlib import sha256
from typing import Final

from pydantic import TypeAdapter

from codex_ticket_dashboard.domain.identifiers import EventId
from codex_ticket_dashboard.ingest.authority_models import next_ingest_sequence
from codex_ticket_dashboard.ingest.identity import BootstrapCode, BootstrapResolution
from codex_ticket_dashboard.ingest.lifecycle_projection import refresh_activity_links
from codex_ticket_dashboard.storage.database import Database

_ROW: Final[TypeAdapter[tuple[str, str] | None]] = TypeAdapter(tuple[str, str] | None)


def resolve_lifecycle_identity(
    database: Database,
    resolution: BootstrapResolution,
    resolution_event_id: EventId,
) -> None:
    """Add a separate effective mapping only after exact applied registry resolution."""
    mapping = resolution.mapping
    if resolution.code is not BootstrapCode.APPLIED or mapping is None:
        return
    with database.transaction() as connection:
        applied = _ROW.validate_python(
            connection.execute(
                """SELECT event_type,project_id FROM ticket_events
            WHERE event_id=? AND event_type='PROJECT_IDENTITY_RESOLVED' AND project_id=?
                AND project_observation_id=?""",
                (resolution_event_id, mapping.project_id, mapping.observation_id),
            ).fetchone()
        )
        observation = _ROW.validate_python(
            connection.execute(
                """SELECT event_id,observed_at FROM lifecycle_observations
            WHERE project_observation_id=? AND project_id IS NULL
            AND project_resolution_state='UNCLASSIFIED' ORDER BY ingest_seq LIMIT 1""",
                (mapping.observation_id,),
            ).fetchone()
        )
        existing = _ROW.validate_python(
            connection.execute(
                """SELECT source_event_id,resolved_project_id FROM event_project_resolutions
            WHERE project_observation_id=? OR resolution_event_id=? LIMIT 1""",
                (mapping.observation_id, resolution_event_id),
            ).fetchone()
        )
        if applied is None or observation is None or existing is not None:
            return
        sequence = next_ingest_sequence(connection)
        _ = connection.execute(
            """INSERT INTO project_observations VALUES (?,'RESOLVED',?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET resolution_state='RESOLVED',
            candidate_project_id=excluded.candidate_project_id""",
            (
                mapping.observation_id,
                "sha256:" + sha256(mapping.observation_id.encode()).hexdigest(),
                mapping.project_id,
                observation[1],
                observation[1],
            ),
        )
        _ = connection.execute(
            "INSERT INTO event_project_resolutions VALUES (?,?,?,?,?)",
            (
                observation[0],
                mapping.observation_id,
                resolution_event_id,
                mapping.project_id,
                sequence,
            ),
        )
        refresh_activity_links(connection, sequence)
