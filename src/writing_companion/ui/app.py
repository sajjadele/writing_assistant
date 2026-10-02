"""Resident Desktop Application & Lifecycle Manager (Adw.Application).

Serves both the in-place Libadwaita HUD window and the management Dashboard,
coordinated via single-instance GApplication DBus IPC.
"""

import sys
import argparse
import asyncio
import threading
from typing import Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from writing_companion.config import load_settings
from writing_companion.storage.sqlite_store import SQLiteStore
from writing_companion.cli import build_engine
from writing_companion.ui.hud import WritingAssistantHUDWindow
from writing_companion.ui.dashboard import DashboardWindow


APPLICATION_ID = "org.sajjad.WritingAssistant"


def notify_extension_paste():
    """Call GNOME Extension DBus bridge to emit virtual Shift+Insert paste."""
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        proxy = Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES,
            None,
            "org.gnome.Shell",
            "/org/gnome/Shell/Extensions/WritingAssistant",
            "org.gnome.Shell.Extensions.WritingAssistant",
            None,
        )
        proxy.call_sync("Paste", None, Gio.DBusCallFlags.NONE, 1000, None)
    except Exception as e:
        # If extension DBus is unavailable, clipboard is already updated
        print(f"[APP] DBus auto-paste notice: {e}", file=sys.stderr)


class WritingAssistantApp(Adw.Application):
    """Single-instance resident Libadwaita Application."""

    def __init__(self):
        super().__init__(
            application_id=APPLICATION_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

        self.settings = load_settings()
        self.store = SQLiteStore(self.settings.db_path)
        self.engine = build_engine()

        self.hud_window: Optional[WritingAssistantHUDWindow] = None
        self.dashboard_window: Optional[DashboardWindow] = None
        self._current_event_id: Optional[int] = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        # Create HUD window once and keep resident
        self.hud_window = WritingAssistantHUDWindow(app=self)

    def do_activate(self):
        # Default activation opens the management dashboard
        self.open_dashboard()

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        """Handle incoming CLI invocations forwarded via DBus."""
        args = command_line.get_arguments()

        parser = argparse.ArgumentParser(description="Writing Assistant Desktop App")
        parser.add_argument("--hud", action="store_true", help="Open floating in-place HUD")
        parser.add_argument("--text", type=str, default="", help="Selected text for HUD evaluation")
        parser.add_argument("--x", type=int, default=0, help="Target screen X coordinate")
        parser.add_argument("--y", type=int, default=0, help="Target screen Y coordinate")
        parser.add_argument("--dashboard", action="store_true", help="Open settings & history dashboard")
        parser.add_argument("--daemon", action="store_true", help="Run resident in background without opening window")
        parser.add_argument("--quit", action="store_true", help="Quit the resident process")

        try:
            parsed, _ = parser.parse_known_args(args[1:])
        except Exception as e:
            command_line.printerr(f"Argument parsing error: {e}\n")
            return 1

        if parsed.quit:
            if self.hud_window:
                self.hud_window.destroy()
            if self.dashboard_window:
                self.dashboard_window.destroy()
            self.quit()
            return 0

        if parsed.dashboard:
            self.open_dashboard()
            return 0

        if parsed.hud:
            if not parsed.text.strip():
                command_line.printerr("Empty text provided for HUD.\n")
                return 0
            self.trigger_hud(parsed.text.strip(), parsed.x, parsed.y)
            return 0

        if parsed.daemon:
            # Stays resident in background
            return 0

        # Default fallback
        self.open_dashboard()
        return 0

    def open_dashboard(self):
        """Open or present the Libadwaita Dashboard."""
        if not self.dashboard_window:
            self.dashboard_window = DashboardWindow(self)
            self.dashboard_window.connect("destroy", self._on_dashboard_destroyed)

        self.dashboard_window.present()

    def _on_dashboard_destroyed(self, window):
        self.dashboard_window = None

    def trigger_hud(self, text: str, x: int = 0, y: int = 0):
        """Show HUD and trigger asynchronous AI analysis."""
        if not self.hud_window:
            self.hud_window = WritingAssistantHUDWindow(app=self)

        # Reload settings in case user updated API keys in dashboard
        self.settings = load_settings()

        # Show loading state
        self.hud_window.show_loading(provider_name=f"Evaluating via {self.settings.ai_provider.upper()}")

        def _worker():
            try:
                # Run evaluation asynchronously
                eng = build_engine()
                response, event_id, backend_name, duration_ms = asyncio.run(eng.process_text(text))
                self._current_event_id = event_id

                def _render():
                    self.hud_window.show_result(
                        response=response,
                        provider_name=backend_name.upper(),
                        duration_ms=duration_ms,
                        on_accept=self._on_hud_accept,
                        on_dismiss=self._on_hud_dismiss,
                        on_copy_only=self._on_hud_copy_only,
                        on_dashboard=self.open_dashboard,
                    )

                GLib.idle_add(_render)

            except Exception as e:
                err_text = str(e)
                GLib.idle_add(lambda: self.hud_window.show_error(err_text))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_hud_accept(self, text: str):
        """User accepted the replacement."""
        if self._current_event_id:
            try:
                self.store.update_acceptance(self._current_event_id, accepted=True)
            except Exception as e:
                print(f"[APP] Failed to record acceptance: {e}", file=sys.stderr)

        # Notify GNOME extension via DBus to paste
        notify_extension_paste()

    def _on_hud_dismiss(self):
        """User dismissed the HUD without applying."""
        if self._current_event_id:
            try:
                self.store.update_acceptance(self._current_event_id, accepted=False)
            except Exception as e:
                print(f"[APP] Failed to record dismissal: {e}", file=sys.stderr)

    def _on_hud_copy_only(self, text: str):
        """User copied text to clipboard."""
        if self._current_event_id:
            try:
                self.store.update_acceptance(self._current_event_id, accepted=True)
            except Exception as e:
                print(f"[APP] Failed to record copy: {e}", file=sys.stderr)


def main():
    app = WritingAssistantApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
