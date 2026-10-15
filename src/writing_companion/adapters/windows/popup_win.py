"""Tkinter frameless in-place popup (Windows counterpart of extension/popup.js).

Dark card (520px), Persian semantic-checkpoint card (amber, RTL),
English suggestion card (blue), diff pills (max 3), footer hints.
Positioned with placement.clamp_popup_position near the cursor.

Bindings: Enter=accept, Esc=dismiss, C=copy-only, D=dashboard(hint).
Runs its own mainloop only when used via run_modal(); the async core call
happens before the window opens so no threading inside tkinter is needed.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from writing_companion.adapters.windows.placement import clamp_popup_position

BG = "#1a1b26"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
AMBER_BG = "#2a2417"
AMBER_BORDER = "#f59e0b"
BLUE_BG = "#16233d"
BLUE_BORDER = "#3b82f6"
GREEN_BG = "#12291c"
GREEN_FG = "#4ade80"
MUTED = "#9ca3af"

POPUP_WIDTH = 520


def force_foreground(hwnd: int) -> bool:
    """Force the popup window to the foreground (beats the foreground lock).

    Windows refuses SetForegroundWindow from a background process unless we
    temporarily attach our thread input to the foreground thread's.
    Pure ctypes, no dependency.
    """
    try:
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        fg = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg, None)
        cur_thread = kernel32.GetCurrentThreadId()
        if fg_thread != cur_thread and fg_thread:
            user32.AttachThreadInput(cur_thread, fg_thread, True)
            try:
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
            finally:
                user32.AttachThreadInput(cur_thread, fg_thread, False)
        else:
            user32.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


class WinPopup:
    """Build-and-show modal popup; result delivered via callback."""

    def __init__(
        self,
        cursor_x: int,
        cursor_y: int,
        loading_text: str = "در حال درک نیت و نگارش طبیعی...",
        master=None,
    ) -> None:
        # Standalone mode (own Tk root) vs daemon mode (Toplevel on the
        # resident hidden root). Toplevel avoids multiple Tk interpreters.
        if master is None:
            self.root = tk.Tk()
            self._own_root = True
        else:
            self.root = tk.Toplevel(master)
            self._own_root = False
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        try:
            self.root.attributes("-alpha", 0.97)
        except Exception:
            pass
        self._cursor_x, self._cursor_y = int(cursor_x), int(cursor_y)
        self._screen_w = self.root.winfo_screenwidth()
        self._screen_h = self.root.winfo_screenheight()
        # Loading window starts compact; autofit() grows it after render.
        place = clamp_popup_position(cursor_x, cursor_y, POPUP_WIDTH, 200, self._screen_w, self._screen_h)
        self.root.geometry(f"{POPUP_WIDTH}x200+{place.x}+{place.y}")

        self._on_accept = None
        self._on_dismiss = None
        self._on_copy = None
        self._closed = False
        # Loading lifecycle: result not yet arrived; an early Enter is
        # remembered and auto-applied the moment the result renders.
        self._loaded = False
        self._pending_accept = False
        self._spin_on = False
        self._spin_dots = 0

        self.body = tk.Frame(self.root, bg=BG, padx=18, pady=14)
        self.body.pack(fill="both", expand=True)

        header = tk.Frame(self.body, bg=BG)
        header.pack(fill="x")
        tk.Label(header, text="✨ WRITING COMPANION", fg=ACCENT, bg=BG, font=("Segoe UI", 10, "bold")).pack(side="left")
        self.badge = tk.Label(header, text="", fg=ACCENT, bg="#232a3d", font=("Segoe UI", 8))
        self.badge.pack(side="right")

        self.content = tk.Frame(self.body, bg=BG)
        self.content.pack(fill="both", expand=True, pady=(10, 6))

        self.status = tk.Label(self.content, text=loading_text, fg=FG, bg=BG, font=("Segoe UI", 10), wraplength=480, justify="left")
        self.status.pack()

        footer = tk.Frame(self.body, bg=BG)
        footer.pack(fill="x", pady=(6, 0))
        tk.Label(footer, text="Enter جایگزینی   Esc انصراف   C کپی", fg=MUTED, bg=BG, font=("Segoe UI", 8)).pack(side="left")

        # Clickable action buttons: mouse always works even when Windows
        # refuses keyboard-focus stealing (foreground lock). Shortcuts
        # remain as the fast path once the popup has focus.
        actions = tk.Frame(self.body, bg=BG)
        actions.pack(fill="x", pady=(8, 0))
        self._mk_button(actions, "✓ جایگزینی", self._accept).pack(side="right", padx=(6, 0))
        self._mk_button(actions, "⧉ کپی", self._copy).pack(side="right", padx=(6, 0))
        self._mk_button(actions, "✕ انصراف", self._dismiss).pack(side="right")

        for seq, fn in (
            ("<Return>", self._accept),
            ("<KP_Enter>", self._accept),
            ("<Escape>", self._dismiss),
            ("<c>", self._copy),
            ("<C>", self._copy),
        ):
            self.root.bind(seq, lambda e, f=fn: f())
            try:
                self.root.bind_all(seq, lambda e, f=fn: f() if not self._closed else None)
            except Exception:
                pass
        # NOTE: no FocusOut auto-dismiss on Windows. A mouse click into
        # another app must NOT silently discard the popup while the user
        # is still deciding; Esc / ✕ is the explicit dismiss path.

    # -- focus & widgets -------------------------------------------------
    @staticmethod
    def _mk_button(parent, text: str, command) -> "tk.Button":
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg="#2b3245",
            fg="white",
            activebackground="#3b82f6",
            activeforeground="white",
            relief="flat",
            padx=12,
            pady=4,
            font=("Segoe UI", 9, "bold"),
            takefocus=True,
        )
        return btn

    def _refocus(self) -> None:
        """Best-effort keyboard-focus grab with retries (foreground lock)."""
        if self._closed:
            return
        try:
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass

    def autofit(self) -> None:
        """Resize the window to fit the rendered content (footer always visible)."""
        try:
            self.root.update_idletasks()
            req = self.body.winfo_reqheight() + 24
            h = max(200, min(req, self._screen_h - 80))
            place = clamp_popup_position(
                self._cursor_x, self._cursor_y, POPUP_WIDTH, h, self._screen_w, self._screen_h
            )
            self.root.geometry(f"{POPUP_WIDTH}x{h}+{place.x}+{place.y}")
        except Exception:
            pass

    def start_spinner(self, base_text: str = "در حال درک نیت و نگارش طبیعی") -> None:
        """Animate the loading label until the result arrives."""
        self._spin_on = True
        self._spin_base = base_text
        self._spin_tick()

    def _spin_tick(self) -> None:
        if not self._spin_on or self._closed or self._loaded:
            return
        try:
            self._spin_dots = (self._spin_dots + 1) % 4
            self.status.config(text=self._spin_base + "." * self._spin_dots)
            self.root.after(350, self._spin_tick)
        except Exception:
            pass

    def _finish_loading(self) -> None:
        self._loaded = True
        self._spin_on = False

    # -- content ---------------------------------------------------------
    def _clear(self) -> None:
        for w in self.content.winfo_children():
            w.destroy()

    def show_error(self, message: str) -> None:
        self._finish_loading()
        self._clear()
        tk.Label(self.content, text=f"⚠️ {message}", fg="#f87171", bg=BG, font=("Segoe UI", 10), wraplength=480, justify="left").pack()
        self.autofit()

    def show_no_change(self, badge: str) -> None:
        self._finish_loading()
        self._clear()
        self.badge.config(text=badge)
        card = tk.Frame(self.content, bg=GREEN_BG, padx=12, pady=10)
        card.pack(fill="x")
        tk.Label(card, text="✓  No Change Needed", fg=GREEN_FG, bg=GREEN_BG, font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(
            card,
            text="جمله شما از نظر گرامری و بیان فنی درست است.",
            fg=GREEN_FG, bg=GREEN_BG, font=("Segoe UI", 10), wraplength=470, justify="right", anchor="e",
        ).pack(fill="x")
        self.autofit()
        if self._pending_accept and not self._closed:
            self._pending_accept = False
            self._accept()

    def show_result(self, meaning_fa: str, corrected: str, changes: list, badge: str) -> None:
        self._finish_loading()
        self._clear()
        self.badge.config(text=badge)
        if meaning_fa:
            fa = tk.Frame(self.content, bg=AMBER_BG, padx=12, pady=8, highlightbackground=AMBER_BORDER, highlightthickness=1)
            fa.pack(fill="x", pady=(0, 8))
            tk.Label(fa, text="💡 برداشت من از منظورتان:", fg=AMBER_BORDER, bg=AMBER_BG, font=("Segoe UI", 9, "bold"), anchor="e", justify="right").pack(fill="x")
            tk.Label(fa, text=meaning_fa, fg="#fef3c7", bg=AMBER_BG, font=("Segoe UI", 10), wraplength=470, justify="right", anchor="e").pack(fill="x")
        en = tk.Frame(self.content, bg=BLUE_BG, padx=12, pady=8, highlightbackground=BLUE_BORDER, highlightthickness=1)
        en.pack(fill="x")
        tk.Label(en, text="✍️ پیشنهاد:", fg=ACCENT, bg=BLUE_BG, font=("Segoe UI", 9, "bold"), anchor="w").pack(fill="x")
        body = tk.Text(en, height=4, wrap="word", bg=BLUE_BG, fg="white", relief="flat", font=("Segoe UI", 10))
        body.insert("1.0", corrected)
        body.config(state="disabled")
        body.pack(fill="x")
        for ch in (changes or [])[:3]:
            orig = ch.get("original", "") if isinstance(ch, dict) else getattr(ch, "original", "")
            repl = ch.get("replacement", "") if isinstance(ch, dict) else getattr(ch, "replacement", "")
            tk.Label(self.content, text=f"{orig}  ➔  {repl}", fg="#86efac", bg=BG, font=("Segoe UI", 9), anchor="w", justify="left").pack(fill="x", pady=1)
        self.autofit()
        # Early Enter during loading: apply the moment the result lands.
        if self._pending_accept and not self._closed:
            self._pending_accept = False
            self._accept()

    # -- events ----------------------------------------------------------
    def _accept(self) -> None:
        if self._closed:
            return
        if not self._loaded:
            # Result not here yet: remember and auto-apply on arrival.
            self._pending_accept = True
            try:
                self.status.config(text="✓ دریافت شد، به محض آماده شدن اعمال می‌شود...")
            except Exception:
                pass
            return
        if self._on_accept:
            self._closed = True
            cb = self._on_accept
            self.root.destroy()
            cb()

    def _dismiss(self) -> None:
        if not self._closed and self._on_dismiss:
            self._closed = True
            cb = self._on_dismiss
            try:
                self.root.destroy()
            except Exception:
                pass
            cb()

    def _copy(self) -> None:
        if not self._closed and self._on_copy:
            self._closed = True
            cb = self._on_copy
            try:
                self.root.destroy()
            except Exception:
                pass
            cb()

    def run_modal(self, on_accept, on_dismiss, on_copy=None) -> None:
        self._on_accept = on_accept
        self._on_dismiss = on_dismiss
        self._on_copy = on_copy or on_dismiss
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        self.root.deiconify()
        self._refocus()
        # Local grab: route all of *our* keyboard/mouse events to the popup
        # so shortcuts work even if a child widget would swallow them.
        try:
            self.root.grab_set()
        except Exception:
            pass
        # Force real OS foreground (AttachThreadInput) for keyboard focus.
        try:
            force_foreground(int(self.root.winfo_id()))
        except Exception:
            pass
        # Retry focus: Windows often denies the first foreground attempt.
        try:
            self.root.after(150, self._refocus)
            self.root.after(500, self._refocus)
        except Exception:
            pass
        if self._own_root:
            self.root.mainloop()
        else:
            # Daemon mode: the hidden root already runs mainloop; block
            # only this popup until it is destroyed.
            try:
                self.root.wait_window(self.root)
            except Exception:
                pass
