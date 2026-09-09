CREATE TABLE lifecycle_mcp_contexts (
    event_id TEXT PRIMARY KEY REFERENCES ticket_events(event_id),
    source_host TEXT NOT NULL,
    thread_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    parent_thread_id TEXT,
    CHECK (parent_thread_id IS NULL OR parent_thread_id != thread_id)
);
CREATE INDEX idx_lifecycle_mcp_contexts_turn ON lifecycle_mcp_contexts(source_host,thread_id,turn_id);
