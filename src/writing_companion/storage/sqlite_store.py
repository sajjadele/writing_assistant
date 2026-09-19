"""SQLite storage manager with WAL mode for local event persistence (ADR-06)."""

import json
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List


SCHEMA_SQL = """
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
"""


class SQLiteStore:
    """Thread-safe local SQLite store for correction events."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

    def record_event(
        self,
        original_text: str,
        interpreted_meaning_fa: Optional[str],
        corrected_text: str,
        is_correct: bool,
        changes: Optional[List[Dict[str, Any]]],
        source_backend: str,
        duration_ms: Optional[int] = None,
        accepted: bool = False,
    ) -> int:
        """Insert a newly processed correction event and return its generated ID."""
        changes_json = json.dumps(changes, ensure_ascii=False) if changes else "[]"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO correction_events (
                    original_text,
                    interpreted_meaning_fa,
                    corrected_text,
                    is_correct,
                    changes_json,
                    accepted,
                    source_backend,
                    duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    original_text,
                    interpreted_meaning_fa,
                    corrected_text,
                    1 if is_correct else 0,
                    changes_json,
                    1 if accepted else 0,
                    source_backend,
                    duration_ms,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_acceptance(self, event_id: int, accepted: bool) -> bool:
        """Update acceptance signal (1 on Enter, 0 on Esc/dismissal)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE correction_events SET accepted = ? WHERE id = ?",
                (1 if accepted else 0, event_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific event by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM correction_events WHERE id = ?", (event_id,))
            row = cursor.fetchone()
            if row:
                d = dict(row)
                d["is_correct"] = bool(d["is_correct"])
                d["accepted"] = bool(d["accepted"])
                if d["changes_json"]:
                    try:
                        d["changes"] = json.loads(d["changes_json"])
                    except Exception:
                        d["changes"] = []
                return d
            return None
