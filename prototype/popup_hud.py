#!/usr/bin/env python3
"""
Frameless Floating Popup HUD Prototype
System-wide English Writing & Learning Companion
Designed for Ubuntu 24.04 / GNOME 46 / Wayland / Pop-Shell Tiling
"""

import sys
import subprocess
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib


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
            "-a", "English Companion",
            "-i", "dialog-information",
            "English Writing Companion",
            "لطفاً ابتدا متن مورد نظرتان را انتخاب (Select) کنید."
        ])
    except Exception:
        pass


class FloatingPopupHUD(Gtk.ApplicationWindow):
    def __init__(self, app, raw_text):
        super().__init__(application=app, title="English Companion Popup")
        self.raw_text = raw_text

        # 1. Frameless Popup Configuration
        self.set_decorated(False)       # No title bar, no min/max/close buttons
        self.set_resizable(False)
        self.set_default_size(440, 200) # Compact card footprint, doesn't take whole screen

        # 2. Modern Compact CSS Styling
        css_provider = Gtk.CssProvider()
        css = """
        window {
            background-color: #181825;
            color: #cdd6f4;
            border-radius: 14px;
            border: 1.5px solid #45475a;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.65);
            padding: 14px 16px;
        }
        .header-title {
            font-size: 11px;
            font-weight: 700;
            color: #89b4fa;
            letter-spacing: 0.8px;
        }
        .suggested-card {
            background-color: #1e1e2e;
            border: 1.5px solid #a6e3a1;
            border-radius: 8px;
            padding: 10px 12px;
            color: #a6e3a1;
            font-size: 14px;
            font-weight: 600;
        }
        .semantic-card {
            background-color: #181825;
            border-left: 3px solid #f9e2af;
            padding: 6px 10px;
            color: #f9e2af;
            font-size: 12px;
        }
        .footer-hint {
            color: #6c7086;
            font-size: 11px;
        }
        """
        css_provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Header Row
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header_lbl = Gtk.Label(label="✨ WRITING COMPANION", xalign=0)
        header_lbl.add_css_class("header-title")
        header_box.append(header_lbl)
        main_box.append(header_box)

        # Transformation logic (Mock / Spike)
        suggested_text, meaning_fa = self.get_transformation(raw_text)
        self.suggested_text = suggested_text

        # Natural English Suggestion (Hero Box)
        sugg_lbl = Gtk.Label(label=suggested_text, xalign=0, wrap=True)
        sugg_lbl.add_css_class("suggested-card")
        main_box.append(sugg_lbl)

        # Semantic Checkpoint (Persian meaning)
        meaning_lbl = Gtk.Label(label=f"💡 منظور: {meaning_fa}", xalign=0, wrap=True)
        meaning_lbl.add_css_class("semantic-card")
        main_box.append(meaning_lbl)

        # Footer Actions Hint
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        enter_hint = Gtk.Label(label="[ Enter ] جایگزینی و کپی", xalign=0)
        enter_hint.add_css_class("footer-hint")
        esc_hint = Gtk.Label(label="[ Esc ] انصراف", xalign=1)
        esc_hint.add_css_class("footer-hint")
        esc_hint.set_hexpand(True)

        footer_box.append(enter_hint)
        footer_box.append(esc_hint)
        main_box.append(footer_box)

        self.set_child(main_box)

        # Keyboard controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

        # Auto-dismiss on focus loss
        self.has_entered_focus = False
        focus_controller = Gtk.EventControllerFocus()
        focus_controller.connect("enter", self.on_focus_enter)
        focus_controller.connect("leave", self.on_focus_leave)
        self.add_controller(focus_controller)

    def on_focus_enter(self, controller):
        self.has_entered_focus = True

    def on_focus_leave(self, controller):
        if self.has_entered_focus:
            print("[POPUP] Focus lost -> Auto dismiss.")
            self.get_application().quit()

    def get_transformation(self, text):
        t = text.strip()
        if "make this button in middle" in t.lower():
            return (
                "Please center this button without breaking the surrounding layout.",
                "می‌خواهید دکمه وسط‌چین شود بدون اینکه چیدمان سایر المان‌ها به هم بریزد."
            )
        elif "سازگار" in t or "compatible" in t.lower():
            return (
                "Can we make this compatible with Windows as well?",
                "می‌خواهید این بخش با ویندوز نیز سازگار شود."
            )
        else:
            return (
                f"I want to make sure that: {t}",
                f"بیان روان و شفاف منظور شما: «{t[:50]}...»"
            )

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            copy_to_clipboard(self.suggested_text)
            print("[POPUP] Enter pressed -> Text copied!")
            self.get_application().quit()
            return True
        elif keyval == Gdk.KEY_Escape:
            print("[POPUP] Esc pressed -> Cancelled.")
            self.get_application().quit()
            return True
        return False


def main():
    selected = get_selected_text()
    if not selected or len(selected) < 2:
        print("[INFO] No text selected.", file=sys.stderr)
        notify_empty()
        sys.exit(0)

    # Ensure WM_CLASS is set properly for Wayland/XWayland and Pop-Shell
    GLib.set_prgname("org.companion.hud")
    GLib.set_application_name("English Companion Popup")

    # application_id matches the Pop-Shell float rule!
    app = Gtk.Application(application_id="org.companion.hud")

    def on_activate(application):
        win = FloatingPopupHUD(application, selected)
        win.present()

    app.connect("activate", on_activate)
    app.run(None)


if __name__ == "__main__":
    main()
