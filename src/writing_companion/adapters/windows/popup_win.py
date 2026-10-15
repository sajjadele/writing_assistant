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


class WinPopup:
    """Build-and-show modal popup; result delivered via callback."""

    def __init__(
        self,
        cursor_x: int,
        cursor_y: int,
        loading_text: str = "در حال درک نیت و نگارش طبیعی...",
    ) -> None:
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)
        try:
            self.root.attributes("-alpha", 0.97)
        except Exception:
            pass
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self._estimated_height = 320
        place = clamp_popup_position(cursor_x, cursor_y, POPUP_WIDTH, self._estimated_height, sw, sh)
        self.root.geometry(f"{POPUP_WIDTH}x{self._estimated_height}+{place.x}+{place.y}")

        self._on_accept: Optional[Callable[[], None]] = None
        self._on_dismiss: Optional[Callable[[], None]] = None
        self._on_copy: Optional[Callable[[], None]] = None
        self._closed = False

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
        tk.Label(footer, text="Enter جایگزینی   Esc انصراف   C کپی   D داشبورد", fg=MUTED, bg=BG, font=("Segoe UI", 8)).pack(side="left")

        self.root.bind("<Return>", lambda e: self._accept())
        self.root.bind("<KP_Enter>", lambda e: self._accept())
        self.root.bind("<Escape>", lambda e: self._dismiss())
        self.root.bind("<c>", lambda e: self._copy())
        self.root.bind("<C>", lambda e: self._copy())
        self.root.bind("<FocusOut>", lambda e: self._dismiss())
        # D opens dashboard on Linux; on Windows show a hint instead.
        self.root.bind("<d>", lambda e: self._dismiss())
        self.root.bind("<D>", lambda e: self._dismiss())

    # -- content ---------------------------------------------------------
    def _clear(self) -> None:
        for w in self.content.winfo_children():
            w.destroy()

    def show_error(self, message: str) -> None:
        self._clear()
        tk.Label(self.content, text=f"⚠️ {message}", fg="#f87171", bg=BG, font=("Segoe UI", 10), wraplength=480, justify="left").pack()

    def show_no_change(self, badge: str) -> None:
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

    def show_result(self, meaning_fa: str, corrected: str, changes: list, badge: str) -> None:
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

    # -- events ----------------------------------------------------------
    def _accept(self) -> None:
        if not self._closed and self._on_accept:
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
        self.root.deiconify()
        try:
            self.root.focus_force()
        except Exception:
            pass
        self.root.mainloop()
