"""Unit tests for Libadwaita HUD and Desktop Application."""

import pytest
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from writing_companion.core.schema import SingleInferenceResponse, ChangeItem
from writing_companion.ui.hud import WritingAssistantHUDWindow
from writing_companion.ui.app import WritingAssistantApp


def test_hud_window_initialization():
    """Verify Libadwaita HUD window initializes with styling and widgets."""
    app = Adw.Application(application_id="org.sajjad.WritingAssistant.Test")
    hud = WritingAssistantHUDWindow(app=app)
    assert hud.get_title() == "Writing Assistant HUD"
    assert hud.get_decorated() is False

    # Test loading state
    hud.show_loading(provider_name="Test Provider")
    assert hud.provider_badge.get_label() == "Test Provider"

    # Test result state
    res = SingleInferenceResponse(
        is_correct=False,
        interpreted_meaning_fa="تست منظور کاربر به زبان فارسی",
        corrected_text="This is a test corrected sentence.",
        changes=[
            ChangeItem(
                original="test sentence",
                replacement="test corrected sentence",
                category="phrasing_idiom",
                explanation_fa="توضیح تستی",
            )
        ],
    )
    hud.show_result(
        response=res,
        provider_name="MOCK",
        duration_ms=120,
    )
    assert hud._current_corrected_text == "This is a test corrected sentence."
    hud.destroy()


def test_hud_window_no_change_needed():
    """Verify 'No Change Needed' state renders correctly."""
    app = Adw.Application(application_id="org.sajjad.WritingAssistant.TestNoChange")
    hud = WritingAssistantHUDWindow(app=app)

    res = SingleInferenceResponse(
        is_correct=True,
        interpreted_meaning_fa="جمله صحیح است",
        corrected_text="Perfect sentence.",
        changes=[],
    )
    hud.show_result(response=res, provider_name="MOCK", duration_ms=50)
    assert hud._current_corrected_text == "Perfect sentence."
    hud.destroy()


def test_writing_assistant_app_initialization():
    """Verify WritingAssistantApp initializes with SQLite store and engine."""
    app = WritingAssistantApp()
    assert app.get_application_id() == "org.sajjad.WritingAssistant"
    assert app.store is not None
    assert app.engine is not None
