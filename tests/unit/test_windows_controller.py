"""Unit tests for the Windows controller data layer (no display needed)."""

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only adapter")


def test_fetch_history_roundtrip(tmp_path, monkeypatch):
    from writing_companion.storage.sqlite_store import SQLiteStore
    import writing_companion.adapters.windows.history_win as hw

    db = tmp_path / "history.db"

    class FakeSettings:
        db_path = db

    monkeypatch.setattr(hw, "load_settings", lambda: FakeSettings())
    store = SQLiteStore(db)
    store.record_event(
        original_text="hi my name",
        interpreted_meaning_fa="معنی",
        corrected_text="Hi, my name.",
        is_correct=False,
        changes=[],
        source_backend="mock",
        duration_ms=5,
    )
    rows = hw.fetch_history()
    assert len(rows) == 1
    assert rows[0]["original_text"] == "hi my name"
    assert rows[0]["source_backend"] == "mock"

    rows = hw.fetch_history(search="nothing-matching")
    assert rows == []


def test_save_settings_roundtrip(tmp_path, monkeypatch):
    import writing_companion.config as config

    fake_file = tmp_path / "settings.json"
    monkeypatch.setattr(config, "USER_CONFIG_FILE", fake_file)
    monkeypatch.setattr(config, "USER_CONFIG_DIR", tmp_path)
    config.save_user_settings({"ai_provider": "gemini", "timeout_ms": 15000})
    s = config.load_settings()
    assert s.ai_provider == "gemini"
    assert s.timeout_ms == 15000


def test_win_app_has_tray_entrypoint():
    from writing_companion.adapters.windows import win_app

    assert callable(win_app.run_tray)
    assert callable(win_app.run_daemon)
    assert callable(win_app.show_popup_for_text)
