CREATE TABLE lifecycle_observations (
    event_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_digest TEXT NOT NULL,
    ingest_seq INTEGER NOT NULL UNIQUE CHECK (ingest_seq > 0),
    observed_at TEXT NOT NULL,
    source_host TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('cli','vscode','unknown')),
    source_event_key TEXT NOT NULL,
    hook_event TEXT NOT NULL,
    event_type TEXT NOT NULL,
    host_session_id TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    turn_id TEXT,
    parent_thread_id TEXT,
    relation_state TEXT NOT NULL CHECK (relation_state IN ('VERIFIED','UNVERIFIED','CONFLICT')),
    project_observation_id TEXT NOT NULL,
    project_id TEXT,
    project_resolution_state TEXT NOT NULL CHECK (project_resolution_state IN ('RESOLVED','UNCLASSIFIED','CONFLICT')),
    coverage TEXT NOT NULL CHECK (coverage IN ('UNVERIFIED','OBSERVED','GAP_DETECTED')),
    mcp_readiness TEXT NOT NULL CHECK (mcp_readiness IN ('READY','UNVERIFIED','UNAVAILABLE')),
    missing_requirements_json TEXT NOT NULL CHECK (json_valid(missing_requirements_json) AND json_type(missing_requirements_json) = 'array'),
    CHECK (parent_thread_id IS NULL OR parent_thread_id != thread_id),
    CHECK ((project_resolution_state = 'RESOLVED' AND project_id IS NOT NULL) OR (project_resolution_state != 'RESOLVED' AND project_id IS NULL))
);
CREATE INDEX idx_lifecycle_observations_turn ON lifecycle_observations(source_host,thread_id,turn_id,ingest_seq);
CREATE INDEX idx_lifecycle_observations_order ON lifecycle_observations(ingest_seq,event_id);
CREATE INDEX idx_lifecycle_observations_parent ON lifecycle_observations(source_host,parent_thread_id,ingest_seq);
CREATE TABLE lifecycle_activity_links (
    observation_event_id TEXT NOT NULL REFERENCES lifecycle_observations(event_id),
    business_event_id TEXT NOT NULL REFERENCES ticket_events(event_id),
    ticket_id TEXT NOT NULL REFERENCES tickets(id),
    linked_ingest_seq INTEGER NOT NULL CHECK (linked_ingest_seq > 0),
    PRIMARY KEY (observation_event_id,business_event_id)
);
CREATE TABLE lifecycle_stop_claims (
    claim_key TEXT PRIMARY KEY,
    source_host TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    original_turn_id TEXT NOT NULL,
    claim_event_id TEXT NOT NULL REFERENCES lifecycle_observations(event_id),
    continuation_turn_id TEXT,
    state TEXT NOT NULL CHECK (state IN ('CLAIMED','CONTINUATION_OBSERVED','NOT_CONTINUED','UNVERIFIED')),
    created_seq INTEGER NOT NULL CHECK (created_seq > 0),
    updated_seq INTEGER NOT NULL CHECK (updated_seq >= created_seq),
    UNIQUE (source_host,thread_id,original_turn_id)
);
