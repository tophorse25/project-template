"""SQLite schema for the demand-intelligence knowledge base.

Improvements over the reference ``super_crawler`` storage:
- A proper ``theme_evidence`` link table (queryable) instead of a JSON blob of ids.
- A ``meta`` table to record the taxonomy version that produced stored labels.
- Indexes for the joins the report/agents actually run.
"""

from __future__ import annotations

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    subreddit TEXT NOT NULL,
    post_id TEXT,
    comment_id TEXT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    score INTEGER,
    comment_count INTEGER,
    created_utc REAL,
    query TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    language TEXT NOT NULL,
    matched_signals TEXT NOT NULL,
    geo_hints TEXT NOT NULL,
    score_history TEXT NOT NULL,
    taxonomy_version TEXT NOT NULL,
    raw TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS themes (
    theme_id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    category TEXT NOT NULL,
    canonical_label TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    sufficiency TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    times_seen INTEGER NOT NULL,
    evidence_count INTEGER NOT NULL,
    subreddit_count INTEGER NOT NULL,
    demand_breakdown TEXT NOT NULL,
    pain_breakdown TEXT NOT NULL,
    geo_distribution TEXT NOT NULL,
    current_scores TEXT NOT NULL,
    previous_scores TEXT NOT NULL,
    confidence TEXT NOT NULL,
    aliases TEXT NOT NULL,
    evidence_ids TEXT NOT NULL,
    history TEXT NOT NULL,
    research_history TEXT NOT NULL,
    latest_recommendation TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS theme_evidence (
    theme_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    linked_at TEXT NOT NULL,
    PRIMARY KEY (theme_id, evidence_id),
    FOREIGN KEY (theme_id) REFERENCES themes(theme_id),
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
);

CREATE TABLE IF NOT EXISTS research_runs (
    run_id TEXT PRIMARY KEY,
    theme_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    input_evidence_ids TEXT NOT NULL,
    findings TEXT NOT NULL,
    scores TEXT NOT NULL,
    geo_analysis TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    sufficiency TEXT NOT NULL,
    limitations TEXT NOT NULL,
    changed_since_last_run TEXT NOT NULL,
    FOREIGN KEY (theme_id) REFERENCES themes(theme_id)
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    pipeline_run_id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    evidence_ingested INTEGER NOT NULL,
    new_evidence INTEGER NOT NULL,
    themes_touched INTEGER NOT NULL,
    themes_queued INTEGER NOT NULL,
    research_runs INTEGER NOT NULL,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_evidence_subreddit ON evidence(subreddit);
CREATE INDEX IF NOT EXISTS idx_theme_evidence_theme ON theme_evidence(theme_id);
CREATE INDEX IF NOT EXISTS idx_theme_evidence_ev ON theme_evidence(evidence_id);
CREATE INDEX IF NOT EXISTS idx_research_theme ON research_runs(theme_id);
CREATE INDEX IF NOT EXISTS idx_themes_product ON themes(product);
"""
