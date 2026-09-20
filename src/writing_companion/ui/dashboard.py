"""Modern Libadwaita/GTK4 Management Dashboard & Settings Application."""

import sys
import json
import asyncio
from typing import Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Pango

from writing_companion.config import load_settings, save_user_settings
from writing_companion.storage.sqlite_store import SQLiteStore
from writing_companion.cli import build_engine


class DashboardWindow(Adw.ApplicationWindow):
    """Main desktop application window for Writing Assistant."""

    def __init__(self, app):
        super().__init__(application=app, title="Writing Assistant — Dashboard")
        self.set_default_size(860, 640)

        self.settings = load_settings()
        self.store = SQLiteStore(self.settings.db_path)
        self.engine = build_engine()

        self._build_ui()

    def _build_ui(self):
        # Root Box
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root_box)

        # HeaderBar with ViewSwitcher
        header = Adw.HeaderBar()
        view_switcher_title = Adw.ViewSwitcherTitle()
        view_switcher_title.set_title("Writing Assistant")
        header.set_title_widget(view_switcher_title)
        root_box.append(header)

        # ViewStack
        self.stack = Adw.ViewStack()
        root_box.append(self.stack)

        # Connect Header ViewSwitcher to Stack
        view_switcher_title.set_stack(self.stack)

        # 1. Settings Page
        settings_page = self._create_settings_page()
        page1 = self.stack.add_titled(settings_page, "settings", "Settings & APIs")
        page1.set_icon_name("emblem-system-symbolic")

        # 2. History Page
        history_page = self._create_history_page()
        page2 = self.stack.add_titled(history_page, "history", "History & Log")
        page2.set_icon_name("document-open-recent-symbolic")

        # 3. Learning Profile Page
        stats_page = self._create_stats_page()
        page3 = self.stack.add_titled(stats_page, "stats", "Learning Profile")
        page3.set_icon_name("dialog-information-symbolic")

    def _create_settings_page(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()

        # Group 1: Provider selection
        provider_group = Adw.PreferencesGroup(title="Active AI Provider", description="Choose the backend used for real-time text analysis")
        page.add(provider_group)

        self.provider_row = Adw.ComboRow(title="Provider Engine")
        providers = Gtk.StringList.new([
            "auto — Smart Cascade (Groq ➔ Gemini ➔ Ollama ➔ Mock)",
            "groq — Cloud Llama 3.3 70B (Fastest: ~250ms)",
            "gemini — Google Gemini 2.0 Flash",
            "ollama — Local Model (Offline / Privacy)",
            "mock — Offline Testing Fixtures",
        ])
        self.provider_row.set_model(providers)

        # Match current config
        idx_map = {"auto": 0, "groq": 1, "gemini": 2, "ollama": 3, "mock": 4}
        self.provider_row.set_selected(idx_map.get(self.settings.ai_provider, 0))
        provider_group.add(self.provider_row)

        # Group 2: Cloud API Keys
        api_group = Adw.PreferencesGroup(title="Cloud API Keys", description="Enter your API keys (stored safely on local disk)")
        page.add(api_group)

        self.groq_key_entry = Adw.PasswordEntryRow(title="Groq API Key")
        self.groq_key_entry.set_text(self.settings.groq_api_key)
        api_group.add(self.groq_key_entry)

        self.gemini_key_entry = Adw.PasswordEntryRow(title="Gemini API Key")
        self.gemini_key_entry.set_text(self.settings.gemini_api_key)
        api_group.add(self.gemini_key_entry)

        # Group 3: Local Ollama
        ollama_group = Adw.PreferencesGroup(title="Local Ollama Server", description="Configure local offline model endpoint")
        page.add(ollama_group)

        self.ollama_host_entry = Adw.EntryRow(title="Ollama URL")
        self.ollama_host_entry.set_text(self.settings.ollama_host)
        ollama_group.add(self.ollama_host_entry)

        self.ollama_model_entry = Adw.EntryRow(title="Ollama Model Name")
        self.ollama_model_entry.set_text(self.settings.ollama_model)
        ollama_group.add(self.ollama_model_entry)

        # Save Button
        save_group = Adw.PreferencesGroup()
        save_btn = Gtk.Button(label="Save All Settings")
        save_btn.add_css_class("suggested-action")
        save_btn.add_css_class("pill")
        save_btn.set_halign(Gtk.Align.CENTER)
        save_btn.set_margin_top(12)
        save_btn.set_margin_bottom(12)
        save_btn.connect("clicked", self._on_save_settings)
        save_group.add(save_btn)
        page.add(save_group)

        # Group 4: Live Test Connection
        test_group = Adw.PreferencesGroup(title="Live Test Connection", description="Test your active AI provider without needing to select text")
        page.add(test_group)

        self.test_input = Adw.EntryRow(title="Test Sentence")
        self.test_input.set_text("Can we [سازگار کنیم] this function with new API?")
        test_group.add(self.test_input)

        test_action_row = Adw.ActionRow(title="Evaluate Sentence Now")
        test_btn = Gtk.Button(label="Test AI")
        test_btn.add_css_class("pill")
        test_btn.connect("clicked", self._on_run_live_test)
        test_action_row.add_suffix(test_btn)
        test_group.add(test_action_row)

        self.test_result_label = Gtk.Label(label="Results will appear here...", wrap=True)
        self.test_result_label.set_margin_top(8)
        self.test_result_label.set_margin_bottom(12)
        self.test_result_label.set_xalign(0.0)
        test_group.add(self.test_result_label)

        return page

    def _create_history_page(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(12)
        box.set_margin_bottom(16)

        # Search Bar & Filter
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", lambda w: self._refresh_history())
        search_box.append(self.search_entry)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.connect("clicked", lambda w: self._refresh_history())
        search_box.append(refresh_btn)
        box.append(search_box)

        # History List in ScrollView
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)

        self.history_list = Gtk.ListBox()
        self.history_list.add_css_class("boxed-list")
        scroll.set_child(self.history_list)
        box.append(scroll)

        self._refresh_history()
        return box

    def _create_stats_page(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        stats_group = Adw.PreferencesGroup(title="Usage & Accuracy Analytics", description="Real-time metrics computed locally from history.db")
        page.add(stats_group)

        stats = self.store.get_stats()

        row1 = Adw.ActionRow(title="Total Translation Events", subtitle="Lifetime sentences analyzed")
        row1.add_suffix(Gtk.Label(label=str(stats.get("total_events", 0))))
        stats_group.add(row1)

        row2 = Adw.ActionRow(title="Accepted Replacements (Enter)", subtitle="Sentences replaced directly in applications")
        row2.add_suffix(Gtk.Label(label=str(stats.get("accepted_events", 0))))
        stats_group.add(row2)

        row3 = Adw.ActionRow(title="Bracket Bridge Translations [واژه]", subtitle="Persian concepts resolved into natural English")
        row3.add_suffix(Gtk.Label(label=str(stats.get("bracket_translations", 0))))
        stats_group.add(row3)

        row4 = Adw.ActionRow(title="Average Latency", subtitle="End-to-end response time")
        row4.add_suffix(Gtk.Label(label=f"{stats.get('avg_duration_ms', 0)} ms"))
        stats_group.add(row4)

        return page

    def _on_save_settings(self, btn):
        prov_keys = ["auto", "groq", "gemini", "ollama", "mock"]
        sel_idx = self.provider_row.get_selected()
        chosen_provider = prov_keys[sel_idx] if sel_idx < len(prov_keys) else "auto"

        data = {
            "ai_provider": chosen_provider,
            "groq_api_key": self.groq_key_entry.get_text().strip(),
            "gemini_api_key": self.gemini_key_entry.get_text().strip(),
            "ollama_host": self.ollama_host_entry.get_text().strip(),
            "ollama_model": self.ollama_model_entry.get_text().strip(),
        }
        save_user_settings(data)
        self.settings = load_settings()
        self.engine = build_engine()

        btn.set_label("✓ Settings Saved!")
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, 2000, lambda: (btn.set_label("Save All Settings"), GLib.SOURCE_REMOVE))

    def _on_run_live_test(self, btn):
        text = self.test_input.get_text().strip()
        if not text:
            return

        self.test_result_label.set_markup("<i>Testing provider in background...</i>")

        def _bg_task():
            try:
                # Reload fresh engine
                eng = build_engine()
                res, event_id, backend, ms = asyncio.run(eng.process_text(text))
                markup = (
                    f"<b>Backend:</b> {backend} ({ms}ms) | <b>Correct:</b> {res.is_correct}\n"
                    f"<b>💡 منظور (FA):</b> {res.interpreted_meaning_fa}\n"
                    f"<b>Suggestion:</b> {res.corrected_text}"
                )
                GLib.idle_add(lambda: self.test_result_label.set_markup(markup))
            except Exception as e:
                err_msg = f"<span foreground='red'>Error: {str(e)}</span>"
                GLib.idle_add(lambda: self.test_result_label.set_markup(err_msg))

        import threading
        threading.Thread(target=_bg_task, daemon=True).start()

    def _refresh_history(self):
        # Clear list
        while True:
            row = self.history_list.get_row_at_index(0)
            if not row:
                break
            self.history_list.remove(row)

        search_query = self.search_entry.get_text() if hasattr(self, "search_entry") else ""
        events = self.store.list_events(limit=50, search=search_query)

        if not events:
            empty_row = Adw.ActionRow(title="No history records found", subtitle="Trigger Ctrl+Alt+G on any text to log interactions.")
            self.history_list.append(empty_row)
            return

        for ev in events:
            status_symbol = "✓ Accepted" if ev["accepted"] else "✗ Dismissed"
            card = Adw.ExpanderRow(
                title=f"{ev['original_text'][:55]}...",
                subtitle=f"{ev['timestamp'][:19]} | {ev['source_backend']} ({ev.get('duration_ms', 0)}ms) | {status_symbol}",
            )

            # Details inside expander
            meaning_row = Adw.ActionRow(
                title="Persian Meaning (💡 منظور)",
                subtitle=ev.get("interpreted_meaning_fa") or "—",
            )
            card.add_row(meaning_row)

            suggest_row = Adw.ActionRow(
                title="Corrected Text",
                subtitle=ev.get("corrected_text") or "—",
            )
            card.add_row(suggest_row)

            self.history_list.append(card)


class DashboardApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.github.sajjadele.writing-assistant")

    def do_activate(self):
        win = DashboardWindow(self)
        win.present()


def run_dashboard():
    """Launch GTK4 / Libadwaita dashboard application."""
    app = DashboardApp()
    return app.run(sys.argv[:1])


if __name__ == "__main__":
    run_dashboard()
