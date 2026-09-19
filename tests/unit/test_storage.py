"""Unit tests for SQLite local storage and WAL mode persistence (ADR-06)."""

import sqlite3
import pytest
from pathlib import Path
from writing_companion.storage.sqlite_store import SQLiteStore


def test_sqlite_store_initialization_and_wal(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    store = SQLiteStore(db_file)

    with sqlite3.connect(str(db_file)) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"


def test_sqlite_record_event_and_retrieve(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    store = SQLiteStore(db_file)

    event_id = store.record_event(
        original_text="Can we [سازگار کنیم] this?",
        interpreted_meaning_fa="آیا می‌توانیم این را سازگار کنیم؟",
        corrected_text="Can we adapt this?",
        is_correct=False,
        changes=[
            {
                "original": "[سازگار کنیم]",
                "replacement": "adapt",
                "category": "bracket_translation",
                "explanation_fa": "معادل مناسب",
            }
        ],
        source_backend="mock",
        duration_ms=180,
        accepted=False,
    )

    assert event_id == 1

    event = store.get_event(event_id)
    assert event is not None
    assert event["original_text"] == "Can we [سازگار کنیم] this?"
    assert event["is_correct"] is False
    assert event["accepted"] is False
    assert event["duration_ms"] == 180
    assert len(event["changes"]) == 1
    assert event["changes"][0]["replacement"] == "adapt"


def test_sqlite_update_acceptance(tmp_path: Path):
    db_file = tmp_path / "test_history.db"
    store = SQLiteStore(db_file)

    event_id = store.record_event(
        original_text="Some text",
        interpreted_meaning_fa=None,
        corrected_text="Some text",
        is_correct=True,
        changes=[],
        source_backend="mock",
    )

    assert store.get_event(event_id)["accepted"] is False

    updated = store.update_acceptance(event_id, accepted=True)
    assert updated is True
    assert store.get_event(event_id)["accepted"] is True
