PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS keyword_targets (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('person', 'organization', 'topic')),
  label TEXT NOT NULL,
  keywords_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_urls (
  id TEXT PRIMARY KEY,
  target_id TEXT NOT NULL,
  source TEXT NOT NULL,
  query TEXT NOT NULL,
  url TEXT NOT NULL,
  title TEXT NOT NULL,
  discovery_method TEXT NOT NULL CHECK (discovery_method IN ('manual', 'official_search', 'import_stub')),
  robots_safety_note TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('queued', 'opened', 'captured', 'dismissed')),
  created_at TEXT NOT NULL,
  FOREIGN KEY (target_id) REFERENCES keyword_targets(id)
);

CREATE TABLE IF NOT EXISTS attachment_metadata (
  id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  file_name TEXT NOT NULL,
  media_type TEXT NOT NULL,
  byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
  sha256 TEXT NOT NULL,
  storage_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
  id TEXT PRIMARY KEY,
  candidate_url_id TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('comment_text', 'page_context', 'screenshot', 'attachment')),
  original_text TEXT NOT NULL,
  normalized_text_hash TEXT NOT NULL,
  source_url TEXT NOT NULL,
  captured_at TEXT NOT NULL,
  capture_hash TEXT NOT NULL,
  immutable INTEGER NOT NULL CHECK (immutable = 1),
  FOREIGN KEY (candidate_url_id) REFERENCES candidate_urls(id)
);

CREATE TABLE IF NOT EXISTS site_public_handles (
  id TEXT PRIMARY KEY,
  site_host TEXT NOT NULL,
  public_handle TEXT NOT NULL,
  evidence_ids_json TEXT NOT NULL,
  note TEXT
);

CREATE TABLE IF NOT EXISTS evidence_clusters (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('exact_duplicate', 'near_duplicate_suggestion')),
  evidence_ids_json TEXT NOT NULL,
  score REAL NOT NULL CHECK (score >= 0 AND score <= 1),
  reviewer_confirmed INTEGER NOT NULL CHECK (reviewer_confirmed IN (0, 1)),
  rationale TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_records (
  id TEXT PRIMARY KEY,
  evidence_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('needs_review', 'approved', 'false_positive', 'excluded')),
  reviewer_note TEXT NOT NULL,
  reviewed_at TEXT NOT NULL,
  FOREIGN KEY (evidence_id) REFERENCES evidence_records(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS report_packages (
  id TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('draft', 'ready', 'exported')),
  evidence_ids_json TEXT NOT NULL,
  cluster_ids_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  export_base_path TEXT
);
