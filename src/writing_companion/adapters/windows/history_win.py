"""Correction history window (Tkinter) for the Windows controller.

Reads the same local SQLite store the core writes to; no network involved.
Single reusable Toplevel per hidden root (re-presented on re-open).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from writing_companion.config import load_settings
from writing_companion.storage.sqlite_store import SQLiteStore

BG = "#1a1b26"
FG = "#cdd6f4"
MUTED = "#9ca3af"
ACCENT = "#89b4fa"


def fetch_history(search: str = "", limit: int = 100) -> list:
    """Headless-safe data layer (unit-testable without a display)."""
    settings = load_settings()
    store = SQLiteStore(settings.db_path)
    return store.list_events(limit=limit, search=search or None)


class HistoryWindow:
    _instance = None

    def __init__(self, master) -> None:
        self.win = tk.Toplevel(master)
        self.win.title("Writing Assistant — History")
        self.win.geometry("720x480")
        self.win.configure(bg=BG)
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass

        top = tk.Frame(self.win, bg=BG)
        top.pack(fill="x", padx=12, pady=(10, 4))
        tk.Label(top, text="📜 Correction history (local only)", fg=ACCENT, bg=BG, font=("Segoe UI", 11, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        search = tk.Entry(top, textvariable=self.search_var, width=28, font=("Segoe UI", 10))
        search.pack(side="right")
        search.bind("<Return>", lambda e: self.reload())
        tk.Button(top, text="↻", command=self.reload, font=("Segoe UI", 10)).pack(side="right", padx=(0, 6))

        cols = ("time", "result", "backend")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=12)
        self.tree.heading("time", text="Time")
        self.tree.heading("result", text="Original → Corrected")
        self.tree.heading("backend", text="Backend")
        self.tree.column("time", width=150, stretch=False)
        self.tree.column("backend", width=110, stretch=False)
        self.tree.pack(fill="both", expand=True, padx=12, pady=4)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_detail())

        self.detail = tk.Text(self.win, height=8, wrap="word", bg="#11111b", fg=FG, font=("Segoe UI", 10))
        self.detail.pack(fill="x", padx=12, pady=(0, 12))
        self._rows: list = []
        self.reload()

    def reload(self) -> None:
        try:
            self._rows = fetch_history(self.search_var.get().strip())
        except Exception as e:
            self._rows = []
            self._show_text(f"Could not load history: {e}")
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        for ev in self._rows:
            status = "✓" if ev.get("accepted") else "✕"
            summary = (ev.get("original_text", "")[:60] + "  →  " + ev.get("corrected_text", "")[:60])
            self.tree.insert("", "end", values=(ev.get("timestamp", ""), f"{status} {summary}", ev.get("source_backend", "")))
        self._show_text(f"{len(self._rows)} events. Select a row for details.")

    def _show_detail(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        ev = self._rows[self.tree.index(sel[0])]
        changes = ev.get("changes") or []
        lines = [
            f"Time: {ev.get('timestamp', '')}   Backend: {ev.get('source_backend', '')}   "
            f"Accepted: {bool(ev.get('accepted'))}   {ev.get('duration_ms', 0)}ms",
            "",
            f"Original: {ev.get('original_text', '')}",
            "",
            f"Corrected: {ev.get('corrected_text', '')}",
            "",
            f"Meaning (FA): {ev.get('interpreted_meaning_fa', '')}",
            "",
        ]
        for ch in changes:
            if isinstance(ch, dict):
                lines.append(f"  • [{ch.get('category', '')}] {ch.get('original', '')} → {ch.get('replacement', '')}")
        self._show_text("\n".join(lines))

    def _show_text(self, text: str) -> None:
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.config(state="disabled")

    def present(self) -> None:
        try:
            self.win.deiconify()
            self.win.lift()
            self.win.focus_force()
        except Exception:
            pass

    @classmethod
    def open(cls, master) -> "HistoryWindow":
        if cls._instance is None or not cls._instance.win.winfo_exists():
            cls._instance = cls(master)
        else:
            cls._instance.reload()
            cls._instance.present()
        return cls._instance
