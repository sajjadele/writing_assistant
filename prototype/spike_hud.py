#!/usr/bin/env python3
"""
Technical Spike #1: Live Wayland HUD & Selection Capture
System-wide English Writing & Learning Companion
Permanent Location: /home/sajjad/Desktop/AI_Enginniering/writing_assistant/prototype/spike_hud.py
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

    # Fallback to regular clipboard
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
        print(f"[SUCCESS] Copied to clipboard & primary: {repr(text)}")
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


class SpikeHUDWindow(Gtk.ApplicationWindow):
    def __init__(self, app, raw_text):
        super().__init__(application=app, title="English Writing Companion — Spike #1")
        self.raw_text = raw_text
        self.set_default_size(520, 320)
        self.set_resizable(False)

        # Style CSS
        css_provider = Gtk.CssProvider()
        css = """
        window {
            background-color: #1e1e2e;
            color: #cdd6f4;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            padding: 16px;
        }
        .title-label {
            font-size: 13px;
            font-weight: bold;
            color: #89b4fa;
            letter-spacing: 0.5px;
        }
        .original-box {
            background-color: #181825;
            border-radius: 8px;
            padding: 10px 12px;
            color: #a6adc8;
            font-size: 14px;
        }
        .suggested-box {
            background-color: #313244;
            border: 1.5px solid #a6e3a1;
            border-radius: 10px;
            padding: 12px 14px;
            color: #a6e3a1;
            font-size: 16px;
            font-weight: 600;
        }
        .semantic-box {
            background-color: #1e1e2e;
            border-left: 3px solid #f9e2af;
            padding: 8px 12px;
            color: #f9e2af;
            font-size: 13px;
        }
        .learning-box {
            color: #b4befe;
            font-size: 12px;
            padding: 4px 6px;
        }
        .footer-label {
            color: #6c7086;
            font-size: 12px;
        }
        .key-badge {
            background-color: #45475a;
            color: #cdd6f4;
            border-radius: 4px;
            padding: 2px 6px;
            font-weight: bold;
        }
        """
        css_provider.load_from_string(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Header
        header = Gtk.Label(label="✨ ENGLISH WRITING COMPANION", xalign=0)
        header.add_css_class("title-label")
        main_box.append(header)

        # Original selection preview
        lbl_orig_title = Gtk.Label(label="متن ورودی شما (Original Selection):", xalign=0)
        lbl_orig_title.add_css_class("footer-label")
        main_box.append(lbl_orig_title)

        orig_box = Gtk.Label(label=raw_text, xalign=0, wrap=True)
        orig_box.add_css_class("original-box")
        main_box.append(orig_box)

        # Mock / Spike transformation for testing
        suggested_text, meaning_fa, learning_note = self.get_spike_transformation(raw_text)
        self.suggested_text = suggested_text

        # 1. Suggested Expression
        lbl_sugg_title = Gtk.Label(label="پیشنهاد دقیق و طبیعی (Natural Expression):", xalign=0)
        lbl_sugg_title.add_css_class("footer-label")
        main_box.append(lbl_sugg_title)

        sugg_box = Gtk.Label(label=suggested_text, xalign=0, wrap=True)
        sugg_box.add_css_class("suggested-box")
        main_box.append(sugg_box)

        # 2. Semantic Checkpoint (برداشت من از منظورتان)
        semantic_box = Gtk.Label(
            label=f"💡 برداشت من از منظورتان:\n{meaning_fa}",
            xalign=0,
            wrap=True
        )
        semantic_box.add_css_class("semantic-box")
        main_box.append(semantic_box)

        # 3. Learning Note (نکته آموزشی)
        if learning_note:
            learn_box = Gtk.Label(label=f"🎓 نکته: {learning_note}", xalign=0, wrap=True)
            learn_box.add_css_class("learning-box")
            main_box.append(learn_box)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        main_box.append(sep)

        # Keyboard Guide Footer
        footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        
        apply_label = Gtk.Label(label="[ Enter ] جایگزینی و کپی در کلیپ‌بورد", xalign=0)
        apply_label.add_css_class("footer-label")
        
        cancel_label = Gtk.Label(label="[ Esc ] انصراف و بستن", xalign=1)
        cancel_label.add_css_label = "footer-label"
        cancel_label.set_hexpand(True)
        
        footer_box.append(apply_label)
        footer_box.append(cancel_label)
        main_box.append(footer_box)

        self.set_child(main_box)

        # Keyboard event controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(key_controller)

    def get_spike_transformation(self, text):
        """Simulate the conservative interpretation & naturalization for Spike #1."""
        t = text.strip()
        
        if "make this button in middle" in t.lower():
            return (
                "Please center this button without breaking the surrounding layout.",
                "می‌خواهید دکمه وسط قرار گیرد بدون اینکه چیدمان بقیه عناصر به هم بریزد.",
                "در طراحی رابط کاربری، برای وسط‌چین کردن از 'center' استفاده می‌شود."
            )
        elif "سازگار" in t or "compatible" in t.lower():
            return (
                "Can we make this code compatible with Windows as well?",
                "می‌خواهید این بخش از کد با ویندوز نیز سازگار شود.",
                "ترکیب استاندارد انگلیسی برای سازگاری: 'compatible with' است."
            )
        else:
            return (
                f"I'd like to ensure that: {t}",
                f"قصد دارید این مفهوم را به صورت روان و شفاف بیان کنید: «{t[:60]}...»",
                "ساختار جمله برای وضوح فنی و طبیعی بودن در زبان انگلیسی بازآرایی شد."
            )

    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            copy_to_clipboard(self.suggested_text)
            print("[USER ACTION] Enter pressed -> Text copied to clipboard!")
            self.get_application().quit()
            return True
        elif keyval == Gdk.KEY_Escape:
            print("[USER ACTION] Esc pressed -> Cancelled without changes.")
            self.get_application().quit()
            return True
        return False


def main():
    selected = get_selected_text()
    if not selected or len(selected) < 2:
        print("[INFO] No text selected. Showing notification.", file=sys.stderr)
        notify_empty()
        sys.exit(0)

    print(f"[SPIKE] Captured text ({len(selected)} chars): {repr(selected[:80])}")

    app = Gtk.Application(application_id="org.antigravity.spike1")

    def on_activate(application):
        win = SpikeHUDWindow(application, selected)
        win.present()

    app.connect("activate", on_activate)
    app.run(None)


if __name__ == "__main__":
    main()
