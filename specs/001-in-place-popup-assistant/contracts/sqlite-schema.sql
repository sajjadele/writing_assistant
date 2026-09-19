-- SQLite Schema for Local Event Persistence & Learning Profile
-- Constitution Principle V / ADR-06 / Feature 001

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS correction_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp               TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    original_text           TEXT NOT NULL,
    interpreted_meaning_fa  TEXT,
    corrected_text          TEXT NOT NULL,
    is_correct              INTEGER NOT NULL CHECK (is_correct IN (0, 1)),
    changes_json            TEXT,
    accepted                INTEGER NOT NULL CHECK (accepted IN (0, 1)),
    source_backend          TEXT NOT NULL,
    duration_ms             INTEGER
);

CREATE INDEX IF NOT EXISTS idx_correction_events_timestamp 
    ON correction_events(timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_correction_events_accepted 
    ON correction_events(accepted);

CREATE INDEX IF NOT EXISTS idx_correction_events_is_correct 
    ON correction_events(is_correct);
