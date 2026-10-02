#!/usr/bin/env python3
"""
Frameless Floating In-Place HUD Prototype & Fallback Runner
System-wide English Writing & Learning Companion
Connects directly to Core AI Engine, SQLite Store, and Vazirmatn Typography.
"""

import sys
import os
import subprocess
import threading
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib

from writing_companion.config import load_settings
from writing_companion.storage.sqlite_store import SQLiteStore
from writing_companion.cli import build_engine


def get_selected_text():
    """Extract primary selection via wl-paste; fallback to regular clipboard."""
    try:
        res = subprocess.run(
            ["wl-paste", "--primary", "--no-newline"],
            capture_output=True,
            text=True,
            timeout=1
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception as e:
        print(f"Error reading primary selection: {e}", file=sys.stderr)

    try:
        res = subprocess.run(
            ["wl-paste", "--no-newline"],
            capture_output=True,
            text=True,
            timeout=1
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception as e:
        print(f"Error reading regular clipboard: {e}", file=sys.stderr)

    return ""


def copy_to_clipboard(text):
    """Set text into both clipboard and primary selection."""
    try:
        subprocess.run(["wl-copy", text], check=True)
        subprocess.run(["wl-copy", "--primary", text], check=True)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to copy text: {e}", file=sys.stderr)
        return False


def notify_empty():
    """Send notification when no text is selected."""
    try:
        subprocess.run([
            "notify-send",
            "-a", "Writing Assistant",
            "-i", "accessories-dictionary-symbolic",
            "Writing Assistant",
            "لطفاً ابتدا متن مورد نظرتان را انتخاب (Select) کنید."
        ])
    except Exception:
        pass


HUD_CSS = """
window {
    background-color: rgba(26, 27, 38, 0.98);
    color: #cdd6f4;
    border-radius: 18px;
    border: 1.5px solid rgba(255, 255, 255, 0.14);
    box-shadow: 0 16px 44px rgba(0, 0, 0, 0.65);
    padding: 16px 20px;
}

.header-title {
    font-size: 13px;
    font-weight: 800;
    color: #89b4fa;
    letter-spacing: 0.5px;
}

.provider-badge {
    background-color: rgba(137, 180, 250, 0.15);
    border: 1px solid rgba(137, 180, 250, 0.3);
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 11px;
    color: #89b4fa;
    font-weight: 600;
}

/* Persian Semantic Checkpoint Card */
.persian-card {
    background-color: rgba(245, 158, 11, 0.08);
    border-right: 4px solid #f59e0b;
    border-radius: 12px;
    padding: 10px 14px;
}

.persian-title {
    font-family: 'Vazirmatn', 'Vazirmatn UI', sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #fbbf24;
}

.persian-body {
    font-family: 'Vazirmatn', 'Vazirmatn UI', sans-serif;
    font-size: 13.5px;
    font-weight: 500;
    line-height: 1.5;
    color: #fef3c7;
}

/* English Suggested Card */
.suggestion-card {
    background-color: rgba(59, 130, 246, 0.10);
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 12px 16px;
}

.suggestion-title {
    font-size: 11.5px;
    font-weight: 700;
    color: #93c5fd;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.suggestion-body {
    font-size: 15px;
    font-weight: 600;
    line-height: 1.45;
    color: #ffffff;
}

/* No Change Needed Card */
.no-change-card {
    background-color: rgba(34, 197, 94, 0.12);
    border-left: 4px solid #22c55e;
    border-radius: 12px;
    padding: 14px 18px;
}

.no-change-title {
    font-size: 14px;
    font-weight: 700;
    color: #4ade80;
}

.no-change-desc {
    font-family: 'Vazirmatn', 'Vazirmatn UI', sans-serif;
    font-size: 12.5px;
    color: #bbf7d0;
}

/* Diff Pills */
.diff-pill {
    background-color: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11.5px;
}

.diff-orig {
    color: #f87171;
    text-decoration: line-through;
}

.diff-arrow {
    color: #9ca3af;
    font-weight: bold;
    padding: 0 4px;
}

.diff-repl {
    color: #4ade80;
    font-weight: 600;
}

/* Footer */
.kbd-badge {
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.20);
    border-radius: 5px;
    padding: 2px 7px;
    font-size: 11px;
    font-weight: 700;
    color: #e5e7eb;
}

.kbd-label {
    font-size: 11.5px;
    color: #9ca3af;
}
"""


class FloatingPopupHUD(Gtk.ApplicationWindow):
    def __init__(self, app, raw_text):
        super().__init__(application=app, title="Writing Assistant HUD — English Companion")
        self.raw_text = raw_text
        self.settings = load_settings()
        self.store = SQLiteStore(self.settings.db_path)
        self.engine = build_engine()

        self.event_id = None
        self.suggested_text = raw_text

        # 1. Frameless Popup Configuration
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(520, -1)

        # 2. Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(HUD_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self._build_ui()
        self._start_evaluation()

    def _build_ui(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        brand = Gtk.Label(label="✨ WRITING ASSISTANT")
        brand.add_css_class("header-title")
        header_box.append(brand)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)

        self.badge = Gtk.Label(label="⚡ Evaluating...")
        self.badge.add_css_class("provider-badge")
        header_box.append(self.badge)

        self.main_box.append(header_box)

        # Dynamic Content Box (Loading / Results)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)

        # Initial Loading state
        loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        loading_box.set_margin_top(12)
        loading_box.set_margin_bottom(12)
        loading_box.set_halign(Gtk.Align.CENTER)
        spinner = Gtk.Spinner()
        spinner.start()
        loading_box.append(spinner)
        loading_lbl = Gtk.Label(label="در حال درک نیت و نگارش طبیعی...")
        loading_lbl.add_css_class("persian-body")
        loading_box.append(loading_lbl)
        self.content_box.append(loading_box)

        self.main_box.append(self.content_box)

        # Separator
        self.main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Footer with keys
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        e_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        k_enter = Gtk.Label(label="Enter")
        k_enter.add_css_class("kbd-badge")
        l_enter = Gtk.Label(label="جایگزینی")
        l_enter.add_css_class("kbd-label")
        e_box.append(k_enter)
        e_box.append(l_enter)
        footer.append(e_box)

        esc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        k_esc = Gtk.Label(label="Esc")
        k_esc.add_css_class("kbd-badge")
        l_esc = Gtk.Label(label="انصراف")
        l_esc.add_css_class("kbd-label")
        esc_box.append(k_esc)
        esc_box.append(l_esc)
        footer.append(esc_box)

        f_spacer = Gtk.Box()
        f_spacer.set_hexpand(True)
        footer.append(f_spacer)

        c_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        k_c = Gtk.Label(label="C")
        k_c.add_css_class("kbd-badge")
        l_c = Gtk.Label(label="کپی")
        l_c.add_css_class("kbd-label")
        c_box.append(k_c)
        c_box.append(l_c)
        footer.append(c_box)

        self.main_box.append(footer)
        self.set_child(self.main_box)

        # Keyboard event controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

    def _start_evaluation(self):
        def _worker():
            try:
                eng = build_engine()
                res, event_id, backend, ms = asyncio.run(eng.process_text(self.raw_text))
                self.event_id = event_id
                self.suggested_text = res.corrected_text
                GLib.idle_add(lambda: self._render_result(res, backend, ms))
            except Exception as e:
                err_text = str(e)
                GLib.idle_add(lambda: self._render_error(err_text))

        threading.Thread(target=_worker, daemon=True).start()

    def _render_result(self, res, backend, ms):
        self._clear_content()
        self.badge.set_label(f"{backend.upper()} • {ms}ms")

        if res.is_correct:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            box.add_css_class("no-change-card")
            t = Gtk.Label(label="✓  No Change Needed", xalign=0)
            t.add_css_class("no-change-title")
            d = Gtk.Label(label="جمله شما از نظر گرامری و بیان فنی کاملاً درست و رسا است.", xalign=0)
            d.add_css_class("no-change-desc")
            box.append(t)
            box.append(d)
            self.content_box.append(box)
        else:
            # 1. Persian Semantic Checkpoint
            if res.interpreted_meaning_fa:
                p_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                p_box.add_css_class("persian-card")
                p_t = Gtk.Label(label="💡 برداشت من از منظورتان (Semantic Checkpoint):", xalign=1)
                p_t.add_css_class("persian-title")
                p_b = Gtk.Label(label=res.interpreted_meaning_fa, xalign=1, wrap=True)
                p_b.add_css_class("persian-body")
                p_box.append(p_t)
                p_box.append(p_b)
                self.content_box.append(p_box)

            # 2. English Suggestion
            s_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            s_box.add_css_class("suggestion-card")
            s_t = Gtk.Label(label="Suggested Expression (طبیعی و روان):", xalign=0)
            s_t.add_css_class("suggestion-title")
            s_b = Gtk.Label(label=res.corrected_text, xalign=0, wrap=True)
            s_b.add_css_class("suggestion-body")
            s_box.append(s_t)
            s_box.append(s_b)

            # 3. Diff Pills
            if res.changes:
                flow = Gtk.FlowBox()
                flow.set_selection_mode(Gtk.SelectionMode.NONE)
                flow.set_max_children_per_line(2)
                flow.set_row_spacing(6)
                flow.set_column_spacing(8)
                flow.set_margin_top(4)

                for ch in res.changes[:3]:
                    pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                    pill.add_css_class("diff-pill")
                    o = Gtk.Label(label=ch.original)
                    o.add_css_class("diff-orig")
                    a = Gtk.Label(label="➔")
                    a.add_css_class("diff-arrow")
                    r = Gtk.Label(label=ch.replacement)
                    r.add_css_class("diff-repl")
                    pill.append(o)
                    pill.append(a)
                    pill.append(r)
                    flow.append(pill)

                s_box.append(flow)

            self.content_box.append(s_box)

    def _render_error(self, err):
        self._clear_content()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("persian-card")
        t = Gtk.Label(label="⚠️ خطا در پردازش متن", xalign=1)
        t.add_css_class("persian-title")
        m = Gtk.Label(label=err, xalign=1, wrap=True)
        m.add_css_class("persian-body")
        box.append(t)
        box.append(m)
        self.content_box.append(box)

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            copy_to_clipboard(self.suggested_text)
            if self.event_id:
                try:
                    self.store.update_acceptance(self.event_id, accepted=True)
                except Exception:
                    pass
            self.get_application().quit()
            return True
        elif keyval == Gdk.KEY_Escape:
            if self.event_id:
                try:
                    self.store.update_acceptance(self.event_id, accepted=False)
                except Exception:
                    pass
            self.get_application().quit()
            return True
        elif keyval in (Gdk.KEY_c, Gdk.KEY_C):
            copy_to_clipboard(self.suggested_text)
            if self.event_id:
                try:
                    self.store.update_acceptance(self.event_id, accepted=True)
                except Exception:
                    pass
            self.get_application().quit()
            return True
        return False

    def _clear_content(self):
        while True:
            child = self.content_box.get_first_child()
            if not child:
                break
            self.content_box.remove(child)


def main():
    selected = get_selected_text()
    if not selected or len(selected) < 2:
        notify_empty()
        sys.exit(0)

    GLib.set_prgname("org.companion.hud")
    GLib.set_application_name("English Companion Popup")

    app = Gtk.Application(application_id="org.companion.hud")

    def on_activate(application):
        win = FloatingPopupHUD(application, selected)
        win.present()

    app.connect("activate", on_activate)
    app.run(None)


if __name__ == "__main__":
    main()
