"""Modern Libadwaita In-Place HUD Window for Writing Assistant.

Renders a beautiful, floating, frameless card adjacent to the text selection
with Vazirmatn Persian typography, diff pills, and Adwaita Dark aesthetics.
"""

import sys
import subprocess
from typing import Optional, Callable

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Pango

from writing_companion.core.schema import SingleInferenceResponse, ChangeItem


HUD_CSS = """
/* Writing Assistant Libadwaita HUD Stylesheet */

.hud-window {
    background-color: rgba(26, 27, 38, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 18px;
    box-shadow: 0 16px 44px rgba(0, 0, 0, 0.6);
    padding: 16px 20px;
    color: #cdd6f4;
}

.hud-header-title {
    font-size: 13px;
    font-weight: 800;
    color: #89b4fa;
    letter-spacing: 0.5px;
}

.hud-provider-badge {
    background-color: rgba(137, 180, 250, 0.15);
    color: #89b4fa;
    border: 1px solid rgba(137, 180, 250, 0.3);
    border-radius: 9999px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}

/* Persian Semantic Checkpoint Card */
.hud-persian-card {
    background-color: rgba(245, 158, 11, 0.08);
    border-right: 4px solid #f59e0b;
    border-radius: 12px;
    padding: 10px 14px;
}

.hud-persian-header {
    font-family: 'Vazirmatn', 'Vazirmatn UI', sans-serif;
    font-size: 12px;
    font-weight: 700;
    color: #fbbf24;
}

.hud-persian-body {
    font-family: 'Vazirmatn', 'Vazirmatn UI', sans-serif;
    font-size: 13.5px;
    font-weight: 500;
    line-height: 1.5;
    color: #fef3c7;
}

/* English Suggested Card */
.hud-suggestion-card {
    background-color: rgba(59, 130, 246, 0.10);
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 12px 16px;
}

.hud-suggestion-header {
    font-size: 11.5px;
    font-weight: 700;
    color: #93c5fd;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.hud-suggestion-body {
    font-size: 15px;
    font-weight: 600;
    line-height: 1.45;
    color: #ffffff;
}

/* No Change Needed Card */
.hud-no-change-card {
    background-color: rgba(34, 197, 94, 0.12);
    border-left: 4px solid #22c55e;
    border-radius: 12px;
    padding: 14px 18px;
}

.hud-no-change-title {
    font-size: 14px;
    font-weight: 700;
    color: #4ade80;
}

.hud-no-change-desc {
    font-family: 'Vazirmatn', 'Vazirmatn UI', sans-serif;
    font-size: 12.5px;
    color: #bbf7d0;
}

/* Diff Pills */
.hud-diff-pill {
    background-color: rgba(255, 255, 255, 0.07);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11.5px;
}

.hud-diff-orig {
    color: #f87171;
    text-decoration: line-through;
}

.hud-diff-arrow {
    color: #9ca3af;
    font-weight: bold;
    padding: 0 4px;
}

.hud-diff-repl {
    color: #4ade80;
    font-weight: 600;
}

/* Footer & Keyboard Badges */
.hud-footer-box {
    padding-top: 4px;
}

.hud-kbd-badge {
    background-color: rgba(255, 255, 255, 0.12);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 5px;
    padding: 2px 7px;
    font-size: 10.5px;
    font-weight: 700;
    color: #e5e7eb;
}

.hud-kbd-label {
    font-size: 11.5px;
    color: #9ca3af;
}
"""


class WritingAssistantHUDWindow(Gtk.Window):
    """Modern Libadwaita/GTK4 In-Place HUD Window."""

    def __init__(self, app=None):
        super().__init__(
            title="Writing Assistant HUD",
            application=app,
            decorated=False,
            resizable=False,
        )

        # Set WM Class / identification
        self.set_default_size(520, -1)

        # Callbacks
        self._on_accept: Optional[Callable[[str], None]] = None
        self._on_dismiss: Optional[Callable[[], None]] = None
        self._on_copy_only: Optional[Callable[[str], None]] = None
        self._on_dashboard: Optional[Callable[[], None]] = None
        self._current_corrected_text: str = ""

        self._load_css()
        self._build_ui()
        self._setup_events()

    def _load_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string(HUD_CSS)
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def _build_ui(self):
        # Root Box with container style
        self.root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.root_box.add_css_class("hud-window")
        self.set_child(self.root_box)

        # 1. Header (Brand + Provider Badge + Close Button)
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        brand_label = Gtk.Label(label="✨ WRITING COMPANION")
        brand_label.add_css_class("hud-header-title")
        brand_label.set_halign(Gtk.Align.START)
        header_box.append(brand_label)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        header_box.append(spacer)

        self.provider_badge = Gtk.Label(label="Groq ~220ms")
        self.provider_badge.add_css_class("hud-provider-badge")
        header_box.append(self.provider_badge)

        close_btn = Gtk.Button(icon_name="window-close-symbolic")
        close_btn.add_css_class("flat")
        close_btn.connect("clicked", lambda b: self.dismiss())
        header_box.append(close_btn)

        self.root_box.append(header_box)

        # 2. Dynamic Content Box (Loading / Result / No Change)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.root_box.append(self.content_box)

        # 3. Separator
        self.sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.root_box.append(self.sep)

        # 4. Footer with keyboard action guides
        self.footer_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        self.footer_box.add_css_class("hud-footer-box")

        # Enter Badge
        enter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        k_enter = Gtk.Label(label="Enter")
        k_enter.add_css_class("hud-kbd-badge")
        lbl_enter = Gtk.Label(label="جایگزینی درجا")
        lbl_enter.add_css_class("hud-kbd-label")
        enter_box.append(k_enter)
        enter_box.append(lbl_enter)
        self.footer_box.append(enter_box)

        # Esc Badge
        esc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        k_esc = Gtk.Label(label="Esc")
        k_esc.add_css_class("hud-kbd-badge")
        lbl_esc = Gtk.Label(label="انصراف")
        lbl_esc.add_css_label = "hud-kbd-label"
        esc_box.append(k_esc)
        esc_box.append(lbl_esc)
        self.footer_box.append(esc_box)

        # Spacer in footer
        f_spacer = Gtk.Box()
        f_spacer.set_hexpand(True)
        self.footer_box.append(f_spacer)

        # C Badge (Copy)
        c_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        k_c = Gtk.Label(label="C")
        k_c.add_css_class("hud-kbd-badge")
        lbl_c = Gtk.Label(label="کپی")
        lbl_c.add_css_class("hud-kbd-label")
        c_box.append(k_c)
        c_box.append(lbl_c)
        self.footer_box.append(c_box)

        # D Badge (Dashboard)
        d_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        k_d = Gtk.Label(label="D")
        k_d.add_css_class("hud-kbd-badge")
        lbl_d = Gtk.Label(label="داشبورد")
        lbl_d.add_css_class("hud-kbd-label")
        d_box.append(k_d)
        d_box.append(lbl_d)
        self.footer_box.append(d_box)

        self.root_box.append(self.footer_box)

    def _setup_events(self):
        # Keyboard Event Controller
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.accept()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.dismiss()
            return True
        elif keyval in (Gdk.KEY_c, Gdk.KEY_C):
            self.copy_only()
            return True
        elif keyval in (Gdk.KEY_d, Gdk.KEY_D):
            if self._on_dashboard:
                self._on_dashboard()
                self.hide()
            return True
        return False

    def show_loading(self, provider_name: str = "Analyzing..."):
        """Render loading state."""
        self._clear_content()
        self.provider_badge.set_label(provider_name)

        loading_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        loading_box.set_margin_top(14)
        loading_box.set_margin_bottom(14)
        loading_box.set_halign(Gtk.Align.CENTER)

        spinner = Gtk.Spinner()
        spinner.start()
        loading_box.append(spinner)

        lbl = Gtk.Label(label="در حال درک نیت و نگارش طبیعی...")
        lbl.add_css_class("hud-persian-body")
        loading_box.append(lbl)

        self.content_box.append(loading_box)
        self.present()

    def show_result(
        self,
        response: SingleInferenceResponse,
        provider_name: str = "Cloud AI",
        duration_ms: int = 0,
        on_accept: Optional[Callable[[str], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
        on_copy_only: Optional[Callable[[str], None]] = None,
        on_dashboard: Optional[Callable[[], None]] = None,
    ):
        """Render the single-inference AI response."""
        self._clear_content()
        self._on_accept = on_accept
        self._on_dismiss = on_dismiss
        self._on_copy_only = on_copy_only
        self._on_dashboard = on_dashboard
        self._current_corrected_text = response.corrected_text

        # Update provider badge
        latency_str = f"{duration_ms}ms" if duration_ms > 0 else "Ready"
        self.provider_badge.set_label(f"{provider_name} • {latency_str}")

        if response.is_correct:
            # 1. No Change Needed
            no_change_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            no_change_card.add_css_class("hud-no-change-card")

            title = Gtk.Label(label="✓  No Change Needed", xalign=0)
            title.add_css_class("hud-no-change-title")
            no_change_card.append(title)

            desc = Gtk.Label(
                label="جمله شما از نظر گرامری، اصطلاحی و بیان فنی کاملاً درست و رسا است.",
                xalign=0,
                wrap=True,
            )
            desc.add_css_class("hud-no-change-desc")
            no_change_card.append(desc)

            self.content_box.append(no_change_card)
        else:
            # 2. Persian Semantic Checkpoint (Anti-Drift)
            if response.interpreted_meaning_fa:
                persian_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                persian_card.add_css_class("hud-persian-card")

                p_header = Gtk.Label(label="💡 برداشت من از منظورتان (Semantic Checkpoint):", xalign=1)
                p_header.add_css_class("hud-persian-header")
                persian_card.append(p_header)

                p_body = Gtk.Label(label=response.interpreted_meaning_fa, xalign=1, wrap=True)
                p_body.add_css_class("hud-persian-body")
                persian_card.append(p_body)

                self.content_box.append(persian_card)

            # 3. English Suggested Expression
            sugg_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            sugg_card.add_css_class("hud-suggestion-card")

            s_header = Gtk.Label(label="Suggested Expression (طبیعی و روان):", xalign=0)
            s_header.add_css_class("hud-suggestion-header")
            sugg_card.append(s_header)

            s_body = Gtk.Label(label=response.corrected_text, xalign=0, wrap=True)
            s_body.add_css_class("hud-suggestion-body")
            sugg_card.append(s_body)

            # 4. Changes / Diff Pills (if available)
            if response.changes:
                diff_flow = Gtk.FlowBox()
                diff_flow.set_selection_mode(Gtk.SelectionMode.NONE)
                diff_flow.set_max_children_per_line(2)
                diff_flow.set_row_spacing(6)
                diff_flow.set_column_spacing(8)
                diff_flow.set_margin_top(4)

                for ch in response.changes[:3]:  # Show top 3 key diffs
                    pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
                    pill.add_css_class("hud-diff-pill")

                    lbl_orig = Gtk.Label(label=ch.original)
                    lbl_orig.add_css_class("hud-diff-orig")
                    lbl_arr = Gtk.Label(label="➔")
                    lbl_arr.add_css_class("hud-diff-arrow")
                    lbl_repl = Gtk.Label(label=ch.replacement)
                    lbl_repl.add_css_class("hud-diff-repl")

                    pill.append(lbl_orig)
                    pill.append(lbl_arr)
                    pill.append(lbl_repl)
                    diff_flow.append(pill)

                sugg_card.append(diff_flow)

            self.content_box.append(sugg_card)

        self.present()

    def show_error(self, message: str):
        """Render error card."""
        self._clear_content()
        err_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        err_box.add_css_class("hud-persian-card")

        lbl_title = Gtk.Label(label="⚠️ خطا در برقراری ارتباط", xalign=1)
        lbl_title.add_css_class("hud-persian-header")
        err_box.append(lbl_title)

        lbl_msg = Gtk.Label(label=message, xalign=1, wrap=True)
        lbl_msg.add_css_class("hud-persian-body")
        err_box.append(lbl_msg)

        self.content_box.append(err_box)
        self.present()

    def accept(self):
        """User pressed Enter to replace text."""
        if self._on_accept and self._current_corrected_text:
            self._copy_to_system_clipboard(self._current_corrected_text)
            self._on_accept(self._current_corrected_text)
        self.hide()

    def copy_only(self):
        """User pressed C to copy only."""
        if self._current_corrected_text:
            self._copy_to_system_clipboard(self._current_corrected_text)
            if self._on_copy_only:
                self._on_copy_only(self._current_corrected_text)
        self.hide()

    def dismiss(self):
        """User pressed Esc or closed."""
        if self._on_dismiss:
            self._on_dismiss()
        self.hide()

    def _copy_to_system_clipboard(self, text: str):
        """Copy text using native wl-copy if in Wayland."""
        try:
            subprocess.run(["wl-copy", text], check=True)
            subprocess.run(["wl-copy", "--primary", text], check=True)
        except Exception as e:
            print(f"[HUD] Clipboard copy warning: {e}", file=sys.stderr)

    def _clear_content(self):
        while True:
            child = self.content_box.get_first_child()
            if not child:
                break
            self.content_box.remove(child)
