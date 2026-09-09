-- allow: SIZE_OK — the initial relational contract is one indivisible forward migration.
CREATE TABLE ingest_sequences (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    last_seq INTEGER NOT NULL CHECK (last_seq >= 0)
);
INSERT INTO ingest_sequences(singleton, last_seq) VALUES (1, 0);

CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    logical_root_key TEXT NOT NULL UNIQUE,
    repo_key TEXT NOT NULL,
    identity_source TEXT NOT NULL CHECK (identity_source IN ('REGISTRY')),
    identity_source_hash TEXT NOT NULL CHECK (substr(identity_source_hash,1,7) = 'sha256:' AND length(identity_source_hash) = 71 AND substr(identity_source_hash,8) NOT GLOB '*[^0-9a-f]*'),
    created_seq INTEGER NOT NULL CHECK (created_seq > 0),
    version INTEGER NOT NULL CHECK (version > 0)
);
CREATE TABLE project_versions (
    project_id TEXT NOT NULL REFERENCES projects(id),
    label TEXT NOT NULL,
    logical_root_key TEXT NOT NULL,
    repo_key TEXT NOT NULL,
    identity_source TEXT NOT NULL CHECK (identity_source IN ('REGISTRY')),
    identity_source_hash TEXT NOT NULL,
    created_seq INTEGER NOT NULL,
    version INTEGER NOT NULL,
    valid_from_ingest_seq INTEGER NOT NULL,
    valid_to_ingest_seq INTEGER,
    PRIMARY KEY (project_id, valid_from_ingest_seq),
    CHECK (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq > valid_from_ingest_seq)
);
CREATE UNIQUE INDEX idx_project_versions_open ON project_versions(project_id) WHERE valid_to_ingest_seq IS NULL;
CREATE INDEX idx_project_versions_asof ON project_versions(created_seq, project_id, valid_from_ingest_seq, valid_to_ingest_seq);
CREATE TRIGGER projects_created_seq_immutable BEFORE UPDATE OF created_seq ON projects
WHEN NEW.created_seq != OLD.created_seq BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_CREATED_SEQ'); END;
CREATE TRIGGER projects_insert_history AFTER INSERT ON projects BEGIN
    INSERT INTO project_versions VALUES (NEW.id,NEW.label,NEW.logical_root_key,NEW.repo_key,NEW.identity_source,NEW.identity_source_hash,NEW.created_seq,NEW.version,NEW.created_seq,NULL);
END;
CREATE TRIGGER projects_update_history AFTER UPDATE ON projects BEGIN
    UPDATE project_versions SET valid_to_ingest_seq=(SELECT last_seq FROM ingest_sequences WHERE singleton=1) WHERE project_id=NEW.id AND valid_to_ingest_seq IS NULL;
    INSERT INTO project_versions VALUES (NEW.id,NEW.label,NEW.logical_root_key,NEW.repo_key,NEW.identity_source,NEW.identity_source_hash,NEW.created_seq,NEW.version,(SELECT last_seq FROM ingest_sequences WHERE singleton=1),NULL);
END;

CREATE TABLE project_observations (
    id TEXT PRIMARY KEY,
    resolution_state TEXT NOT NULL CHECK (resolution_state IN ('RESOLVED','UNCLASSIFIED','CONFLICT')),
    path_fingerprint TEXT NOT NULL,
    candidate_project_id TEXT REFERENCES projects(id),
    first_observed_at TEXT NOT NULL,
    last_observed_at TEXT NOT NULL
);
CREATE TABLE project_policies (
    project_id TEXT PRIMARY KEY REFERENCES projects(id),
    wiki_authority TEXT NOT NULL,
    git_authority TEXT NOT NULL,
    authority_ceiling TEXT NOT NULL,
    evidence_ref TEXT NOT NULL,
    evidence_hash TEXT NOT NULL,
    policy_snapshot_id TEXT NOT NULL,
    resolved_at TEXT NOT NULL
);
CREATE TABLE threads (
    session_id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id),
    source_kind TEXT NOT NULL CHECK (source_kind IN ('cli','vscode','unknown')),
    observed_at TEXT NOT NULL
);
CREATE TABLE tickets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    record_type TEXT NOT NULL CHECK (record_type IN ('WORK_TICKET','DISCUSSION_LOG','UNCLASSIFIED')),
    status TEXT NOT NULL CHECK (status IN ('BACKLOG','PLANNED','IN_PROGRESS','WAITING_USER','BLOCKED','IN_REVIEW','COMPLETED','CANCELLED')),
    needs_triage INTEGER NOT NULL CHECK (needs_triage IN (0,1)),
    summary TEXT NOT NULL,
    next_step TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_seq INTEGER NOT NULL CHECK (created_seq > 0),
    closed_at TEXT,
    closed_reason TEXT,
    version INTEGER NOT NULL CHECK (version > 0),
    CHECK ((closed_at IS NULL) = (closed_reason IS NULL))
);
CREATE INDEX idx_tickets_created ON tickets(created_seq, id);
CREATE TABLE ticket_versions (
    ticket_id TEXT NOT NULL REFERENCES tickets(id),
    project_id TEXT NOT NULL REFERENCES projects(id),
    title TEXT NOT NULL,
    record_type TEXT NOT NULL,
    status TEXT NOT NULL,
    needs_triage INTEGER NOT NULL,
    summary TEXT NOT NULL,
    next_step TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    created_seq INTEGER NOT NULL,
    closed_at TEXT,
    closed_reason TEXT,
    version INTEGER NOT NULL,
    valid_from_ingest_seq INTEGER NOT NULL,
    valid_to_ingest_seq INTEGER,
    PRIMARY KEY (ticket_id, valid_from_ingest_seq),
    CHECK (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq > valid_from_ingest_seq)
);
CREATE UNIQUE INDEX idx_ticket_versions_open ON ticket_versions(ticket_id) WHERE valid_to_ingest_seq IS NULL;
CREATE INDEX idx_ticket_versions_asof ON ticket_versions(created_seq, ticket_id, valid_from_ingest_seq, valid_to_ingest_seq);
CREATE TRIGGER tickets_created_seq_immutable BEFORE UPDATE OF created_seq ON tickets
WHEN NEW.created_seq != OLD.created_seq BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_CREATED_SEQ'); END;
CREATE TRIGGER tickets_insert_history AFTER INSERT ON tickets BEGIN
    INSERT INTO ticket_versions VALUES (NEW.id,NEW.project_id,NEW.title,NEW.record_type,NEW.status,NEW.needs_triage,NEW.summary,NEW.next_step,NEW.created_at,NEW.updated_at,NEW.created_seq,NEW.closed_at,NEW.closed_reason,NEW.version,NEW.created_seq,NULL);
END;
CREATE TRIGGER tickets_update_history AFTER UPDATE ON tickets BEGIN
    UPDATE ticket_versions SET valid_to_ingest_seq=(SELECT last_seq FROM ingest_sequences WHERE singleton=1) WHERE ticket_id=NEW.id AND valid_to_ingest_seq IS NULL;
    INSERT INTO ticket_versions VALUES (NEW.id,NEW.project_id,NEW.title,NEW.record_type,NEW.status,NEW.needs_triage,NEW.summary,NEW.next_step,NEW.created_at,NEW.updated_at,NEW.created_seq,NEW.closed_at,NEW.closed_reason,NEW.version,(SELECT last_seq FROM ingest_sequences WHERE singleton=1),NULL);
END;

CREATE TABLE ticket_threads (
    ticket_id TEXT NOT NULL REFERENCES tickets(id),
    session_id TEXT NOT NULL REFERENCES threads(session_id),
    PRIMARY KEY (ticket_id, session_id)
);
CREATE TABLE turns (
    session_id TEXT NOT NULL REFERENCES threads(session_id),
    turn_id TEXT NOT NULL,
    stop_state TEXT NOT NULL,
    PRIMARY KEY (session_id, turn_id)
);
CREATE TABLE work_items (
    id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets(id),
    parent_work_item_id TEXT REFERENCES work_items(id),
    kind TEXT NOT NULL CHECK (kind IN ('TASK','SUBTASK','UNCLASSIFIED')),
    status TEXT NOT NULL CHECK (status IN ('PLANNED','IN_PROGRESS','WAITING_USER','BLOCKED','RESULT_REPORTED','CANCELLED','SUPERSEDED')),
    summary TEXT NOT NULL,
    created_seq INTEGER NOT NULL CHECK (created_seq > 0),
    version INTEGER NOT NULL CHECK (version > 0)
);
CREATE INDEX idx_work_items_ticket ON work_items(ticket_id, created_seq, id);
CREATE TRIGGER work_items_created_seq_immutable BEFORE UPDATE OF created_seq ON work_items
WHEN NEW.created_seq != OLD.created_seq BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_CREATED_SEQ'); END;

CREATE TABLE ticket_events (
    event_id TEXT PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE CHECK (substr(idempotency_key,1,7) = 'sha256:' AND length(idempotency_key) = 71 AND substr(idempotency_key,8) NOT GLOB '*[^0-9a-f]*'),
    payload_digest TEXT NOT NULL CHECK (substr(payload_digest,1,7) = 'sha256:' AND length(payload_digest) = 71 AND substr(payload_digest,8) NOT GLOB '*[^0-9a-f]*'),
    event_type TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK (schema_version > 0),
    occurred_at TEXT NOT NULL,
    received_at TEXT,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('USER','CODEX','SYSTEM','OBSERVER','RECOVERY')),
    origin TEXT NOT NULL CHECK (origin IN ('MCP_TOOL','HOOK','COLLECTOR','APP_SERVER','RECOVERY')),
    authority TEXT NOT NULL CHECK (authority IN ('CODEX_PREFLIGHT','CODEX_EXECUTION','CODEX_RESULT','USER_EXPLICIT','SYSTEM_DERIVED')),
    project_observation_id TEXT NOT NULL,
    project_id TEXT,
    project_resolution_state TEXT NOT NULL CHECK (project_resolution_state IN ('RESOLVED','UNCLASSIFIED','CONFLICT')),
    repo_key TEXT,
    session_id TEXT NOT NULL,
    turn_id TEXT,
    ticket_id TEXT,
    work_item_id TEXT,
    causation_event_id TEXT,
    depends_on_event_ids_json TEXT NOT NULL CHECK (json_valid(depends_on_event_ids_json) AND json_type(depends_on_event_ids_json) = 'array'),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json) AND json_type(payload_json) = 'object'),
    ingest_seq INTEGER NOT NULL UNIQUE CHECK (ingest_seq > 0),
    CHECK (
        (project_resolution_state = 'RESOLVED' AND project_id IS NOT NULL)
        OR (project_resolution_state IN ('UNCLASSIFIED','CONFLICT') AND project_id IS NULL)
    ),
    CHECK (work_item_id IS NULL OR ticket_id IS NOT NULL)
);
CREATE INDEX idx_ticket_events_order ON ticket_events(ingest_seq, event_id);
CREATE INDEX idx_ticket_events_causation ON ticket_events(causation_event_id);
CREATE INDEX idx_ticket_events_project_order ON ticket_events(project_id, ingest_seq, event_id);
CREATE INDEX idx_ticket_events_ticket_type_order ON ticket_events(ticket_id, event_type, ingest_seq, event_id);
CREATE INDEX idx_ticket_events_work_item_type_order ON ticket_events(work_item_id, event_type, ingest_seq, event_id);
CREATE INDEX idx_ticket_events_session_turn_order ON ticket_events(session_id, turn_id, ingest_seq, event_id);
CREATE TRIGGER ticket_events_immutable BEFORE UPDATE ON ticket_events BEGIN
    SELECT RAISE(ABORT, 'IMMUTABLE_TICKET_EVENT');
END;
CREATE TRIGGER ticket_events_no_delete BEFORE DELETE ON ticket_events BEGIN
    SELECT RAISE(ABORT, 'IMMUTABLE_TICKET_EVENT');
END;

CREATE TABLE compliance_gates (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id),
    ticket_id TEXT REFERENCES tickets(id),
    work_item_id TEXT REFERENCES work_items(id),
    gate_type TEXT NOT NULL CHECK (gate_type IN ('GIT','WIKI')),
    requirement TEXT NOT NULL CHECK (requirement IN ('REQUIRED','ADVISORY','NOT_APPLICABLE')),
    status TEXT NOT NULL CHECK (status IN ('PENDING','SATISFIED','STATUS-ONLY','COMMIT-PENDING','PUSH-PENDING','UPDATE-PENDING','BLOCKED','UNVERIFIED','COMPLIANCE_INCOMPLETE','N/A')),
    evidence_ref TEXT,
    evidence_hash TEXT,
    created_seq INTEGER NOT NULL CHECK (created_seq > 0),
    version INTEGER NOT NULL CHECK (version > 0),
    UNIQUE (ticket_id, work_item_id, gate_type)
);
CREATE TABLE compliance_gate_versions (
    gate_id TEXT NOT NULL REFERENCES compliance_gates(id),
    project_id TEXT NOT NULL REFERENCES projects(id),
    ticket_id TEXT,
    work_item_id TEXT,
    gate_type TEXT NOT NULL,
    requirement TEXT NOT NULL,
    status TEXT NOT NULL,
    evidence_ref TEXT,
    evidence_hash TEXT,
    created_seq INTEGER NOT NULL,
    version INTEGER NOT NULL,
    valid_from_ingest_seq INTEGER NOT NULL,
    valid_to_ingest_seq INTEGER,
    PRIMARY KEY (gate_id, valid_from_ingest_seq),
    CHECK (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq > valid_from_ingest_seq)
);
CREATE UNIQUE INDEX idx_compliance_gate_versions_open ON compliance_gate_versions(gate_id) WHERE valid_to_ingest_seq IS NULL;
CREATE INDEX idx_compliance_gate_versions_asof ON compliance_gate_versions(created_seq, gate_id, valid_from_ingest_seq, valid_to_ingest_seq);
CREATE TRIGGER compliance_gates_created_seq_immutable BEFORE UPDATE OF created_seq ON compliance_gates
WHEN NEW.created_seq != OLD.created_seq BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_CREATED_SEQ'); END;
CREATE TRIGGER compliance_gates_insert_history AFTER INSERT ON compliance_gates BEGIN
    INSERT INTO compliance_gate_versions VALUES (NEW.id,NEW.project_id,NEW.ticket_id,NEW.work_item_id,NEW.gate_type,NEW.requirement,NEW.status,NEW.evidence_ref,NEW.evidence_hash,NEW.created_seq,NEW.version,NEW.created_seq,NULL);
END;
CREATE TRIGGER compliance_gates_update_history AFTER UPDATE ON compliance_gates BEGIN
    UPDATE compliance_gate_versions SET valid_to_ingest_seq=(SELECT last_seq FROM ingest_sequences WHERE singleton=1) WHERE gate_id=NEW.id AND valid_to_ingest_seq IS NULL;
    INSERT INTO compliance_gate_versions VALUES (NEW.id,NEW.project_id,NEW.ticket_id,NEW.work_item_id,NEW.gate_type,NEW.requirement,NEW.status,NEW.evidence_ref,NEW.evidence_hash,NEW.created_seq,NEW.version,(SELECT last_seq FROM ingest_sequences WHERE singleton=1),NULL);
END;

CREATE TABLE pending_dependencies (
    event_id TEXT NOT NULL,
    dependency_event_id TEXT NOT NULL,
    payload_digest TEXT NOT NULL CHECK (substr(payload_digest,1,7) = 'sha256:' AND length(payload_digest) = 71 AND substr(payload_digest,8) NOT GLOB '*[^0-9a-f]*'),
    failure_code TEXT,
    PRIMARY KEY (event_id, dependency_event_id)
);
CREATE INDEX idx_pending_dependencies_parent ON pending_dependencies(dependency_event_id, event_id);
CREATE TABLE decision_consumptions (
    decision_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets(id),
    transition_event_id TEXT NOT NULL UNIQUE REFERENCES ticket_events(event_id),
    consumed_at_ingest_seq INTEGER NOT NULL UNIQUE
);
CREATE INDEX idx_decision_consumptions_ticket_seq ON decision_consumptions(ticket_id, consumed_at_ingest_seq);
CREATE TABLE ingest_receipts (
    idempotency_key TEXT PRIMARY KEY CHECK (substr(idempotency_key,1,7) = 'sha256:' AND length(idempotency_key) = 71 AND substr(idempotency_key,8) NOT GLOB '*[^0-9a-f]*'),
    event_id TEXT NOT NULL UNIQUE,
    payload_digest TEXT NOT NULL CHECK (substr(payload_digest,1,7) = 'sha256:' AND length(payload_digest) = 71 AND substr(payload_digest,8) NOT GLOB '*[^0-9a-f]*'),
    state TEXT NOT NULL CHECK (state IN ('RECEIVED','PENDING_IDENTITY','PENDING_DEPENDENCY','APPLIED','DEPENDENCY_FAILED','REJECTED')),
    ingest_seq INTEGER UNIQUE CHECK (ingest_seq IS NULL OR ingest_seq > 0),
    failure_code TEXT,
    failed_dependency_event_id TEXT,
    root_failed_dependency_event_id TEXT,
    archive_state TEXT CHECK (archive_state IN ('PENDING','ARCHIVED','FAILED')),
    archive_error_code TEXT,
    archive_payload_sha256 TEXT,
    CHECK (state != 'APPLIED' OR ingest_seq IS NOT NULL),
    CHECK (state != 'DEPENDENCY_FAILED' OR (failure_code IS NOT NULL AND failed_dependency_event_id IS NOT NULL AND root_failed_dependency_event_id IS NOT NULL)),
    CHECK (
        (archive_state IS NULL AND archive_error_code IS NULL AND archive_payload_sha256 IS NULL)
        OR (archive_state IN ('PENDING','ARCHIVED') AND archive_error_code IS NULL AND length(archive_payload_sha256) = 64 AND archive_payload_sha256 NOT GLOB '*[^0-9a-f]*')
        OR (archive_state = 'FAILED' AND archive_error_code IS NOT NULL AND length(archive_payload_sha256) = 64 AND archive_payload_sha256 NOT GLOB '*[^0-9a-f]*')
    )
);
CREATE INDEX idx_receipts_event ON ingest_receipts(event_id, state);
CREATE TRIGGER ingest_receipts_seq_immutable BEFORE UPDATE OF ingest_seq ON ingest_receipts
WHEN NOT (
    OLD.ingest_seq IS NULL
    AND NEW.ingest_seq IS NOT NULL
    AND OLD.state IN ('PENDING_IDENTITY','PENDING_DEPENDENCY')
) BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_INGEST_SEQ'); END;
CREATE TABLE dead_letters (
    event_id TEXT PRIMARY KEY,
    payload_digest TEXT NOT NULL CHECK (substr(payload_digest,1,7) = 'sha256:' AND length(payload_digest) = 71 AND substr(payload_digest,8) NOT GLOB '*[^0-9a-f]*'),
    diagnostic_code TEXT NOT NULL,
    field_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE ingest_issues (
    id TEXT PRIMARY KEY,
    event_id TEXT,
    code TEXT NOT NULL,
    field_path TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('OPEN','RESOLVED')),
    created_seq INTEGER NOT NULL CHECK (created_seq > 0),
    version INTEGER NOT NULL CHECK (version > 0)
);
CREATE TABLE ingest_issue_versions (
    issue_id TEXT NOT NULL REFERENCES ingest_issues(id),
    event_id TEXT,
    code TEXT NOT NULL,
    field_path TEXT NOT NULL,
    state TEXT NOT NULL,
    created_seq INTEGER NOT NULL,
    version INTEGER NOT NULL,
    valid_from_ingest_seq INTEGER NOT NULL,
    valid_to_ingest_seq INTEGER,
    PRIMARY KEY (issue_id, valid_from_ingest_seq),
    CHECK (valid_to_ingest_seq IS NULL OR valid_to_ingest_seq > valid_from_ingest_seq)
);
CREATE UNIQUE INDEX idx_ingest_issue_versions_open ON ingest_issue_versions(issue_id) WHERE valid_to_ingest_seq IS NULL;
CREATE INDEX idx_ingest_issue_versions_asof ON ingest_issue_versions(created_seq, issue_id, valid_from_ingest_seq, valid_to_ingest_seq);
CREATE TRIGGER ingest_issues_created_seq_immutable BEFORE UPDATE OF created_seq ON ingest_issues
WHEN NEW.created_seq != OLD.created_seq BEGIN SELECT RAISE(ABORT, 'IMMUTABLE_CREATED_SEQ'); END;
CREATE TRIGGER ingest_issues_insert_history AFTER INSERT ON ingest_issues BEGIN
    INSERT INTO ingest_issue_versions VALUES (NEW.id,NEW.event_id,NEW.code,NEW.field_path,NEW.state,NEW.created_seq,NEW.version,NEW.created_seq,NULL);
END;
CREATE TRIGGER ingest_issues_update_history AFTER UPDATE ON ingest_issues BEGIN
    UPDATE ingest_issue_versions SET valid_to_ingest_seq=(SELECT last_seq FROM ingest_sequences WHERE singleton=1) WHERE issue_id=NEW.id AND valid_to_ingest_seq IS NULL;
    INSERT INTO ingest_issue_versions VALUES (NEW.id,NEW.event_id,NEW.code,NEW.field_path,NEW.state,NEW.created_seq,NEW.version,(SELECT last_seq FROM ingest_sequences WHERE singleton=1),NULL);
END;

CREATE TABLE event_project_resolutions (
    source_event_id TEXT PRIMARY KEY,
    project_observation_id TEXT NOT NULL REFERENCES project_observations(id),
    resolution_event_id TEXT NOT NULL UNIQUE REFERENCES ticket_events(event_id),
    resolved_project_id TEXT NOT NULL REFERENCES projects(id),
    resolved_at_ingest_seq INTEGER NOT NULL
);
CREATE TABLE turn_relations (
    relation_event_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES tickets(id),
    session_id TEXT NOT NULL,
    source_turn_id TEXT NOT NULL,
    related_turn_id TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('USER_FOLLOWUP','STOP_CONTINUATION','REOPEN_FOLLOWUP')),
    UNIQUE (ticket_id, session_id, source_turn_id, related_turn_id, relation_type)
);
CREATE INDEX idx_turn_relations_related_turn ON turn_relations(session_id, related_turn_id, relation_type);
CREATE TABLE hook_runtime_snapshots (
    id TEXT PRIMARY KEY,
    handler_fingerprint TEXT NOT NULL,
    layer_count INTEGER NOT NULL CHECK (layer_count >= 0),
    trust_state TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
CREATE TABLE hook_decisions (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    decision TEXT NOT NULL CHECK (decision IN ('ALLOW','BLOCK')),
    UNIQUE (session_id, turn_id, ordinal)
);
CREATE TABLE hook_aggregate_outcomes (
    event_id TEXT PRIMARY KEY,
    observer_decision_event_id TEXT NOT NULL REFERENCES hook_decisions(event_id),
    outcome TEXT NOT NULL CHECK (outcome IN ('CONTINUED','NOT_CONTINUED'))
);
CREATE TABLE app_server_observations (
    id TEXT PRIMARY KEY,
    method TEXT NOT NULL CHECK (method IN ('initialize','thread/list','thread/read')),
    use_state_db_only INTEGER NOT NULL CHECK (use_state_db_only IN (0,1)),
    source_kinds TEXT NOT NULL,
    include_turns INTEGER NOT NULL CHECK (include_turns IN (0,1)),
    allowlist_manifest_hash TEXT,
    observed_source_kind TEXT CHECK (observed_source_kind IN ('cli','vscode','unknown')),
    result_code TEXT NOT NULL
);
CREATE TABLE security_startup_checks (
    id TEXT PRIMARY KEY,
    owner_sid_digest TEXT NOT NULL,
    owner_only INTEGER NOT NULL CHECK (owner_only IN (0,1)),
    inheritance_blocked INTEGER NOT NULL CHECK (inheritance_blocked IN (0,1)),
    fixed_volume INTEGER NOT NULL CHECK (fixed_volume IN (0,1)),
    reparse_free INTEGER NOT NULL CHECK (reparse_free IN (0,1)),
    final_path_contained INTEGER NOT NULL CHECK (final_path_contained IN (0,1)),
    loopback_bound INTEGER NOT NULL CHECK (loopback_bound IN (0,1)),
    host_allowlist_valid INTEGER NOT NULL CHECK (host_allowlist_valid IN (0,1)),
    no_store_enabled INTEGER NOT NULL CHECK (no_store_enabled IN (0,1)),
    checked_at TEXT NOT NULL
);
