"""Settings window (Tkinter) for the Windows controller.

Edits user-level settings persisted to ~/.config/writing_companion/settings.json
(same file the core reads). Secrets stay local; nothing is transmitted.
Single reusable Toplevel per hidden root.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from writing_companion.config import load_settings, save_user_settings

BG = "#1a1b26"
FG = "#cdd6f4"
MUTED = "#9ca3af"
ACCENT = "#89b4fa"
PROVIDERS = ("auto", "groq", "gemini", "ollama", "mock")


class SettingsWindow:
    _instance = None

    def __init__(self, master) -> None:
        self.win = tk.Toplevel(master)
        self.win.title("Writing Assistant — Settings")
        self.win.geometry("480x420")
        self.win.configure(bg=BG)
        try:
            self.win.attributes("-topmost", True)
        except Exception:
            pass

        body = tk.Frame(self.win, bg=BG, padx=16, pady=12)
        body.pack(fill="both", expand=True)
        tk.Label(body, text="⚙️ Settings (stored locally)", fg=ACCENT, bg=BG, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        s = load_settings()
        self.entries: dict = {}
        self._row(body, "ai_provider", "Provider", s.ai_provider, combo=PROVIDERS)
        self._row(body, "groq_api_key", "Groq API key", s.groq_api_key, secret=True)
        self._row(body, "gemini_api_key", "Gemini API key", s.gemini_api_key, secret=True)
        self._row(body, "ollama_host", "Ollama host", s.ollama_host)
        self._row(body, "ollama_model", "Ollama model", s.ollama_model)
        self._row(body, "timeout_ms", "Timeout (ms)", str(s.timeout_ms))

        self.msg = tk.Label(body, text="", fg=MUTED, bg=BG, font=("Segoe UI", 9))
        self.msg.pack(pady=(8, 0))

        btns = tk.Frame(body, bg=BG)
        btns.pack(fill="x", pady=(10, 0))
        tk.Button(btns, text="💾 Save", command=self.save, bg="#2b3245", fg="white",
                  activebackground="#3b82f6", relief="flat", padx=14, pady=4,
                  font=("Segoe UI", 10, "bold")).pack(side="right")
        tk.Button(btns, text="Close", command=self.win.destroy, relief="flat",
                  padx=14, pady=4, font=("Segoe UI", 10)).pack(side="right", padx=(0, 8))

    def _row(self, parent, key, label, value, combo=None, secret=False) -> None:
        tk.Label(parent, text=label, fg=FG, bg=BG, font=("Segoe UI", 10)).pack(anchor="w", pady=(6, 0))
        if combo:
            var = tk.StringVar(value=value if value in combo else combo[0])
            ttk.OptionMenu(parent, var, var.get(), *combo).pack(fill="x")
            self.entries[key] = var
        else:
            var = tk.StringVar(value=value or "")
            tk.Entry(parent, textvariable=var, show="•" if secret else "",
                     font=("Segoe UI", 10)).pack(fill="x")
            self.entries[key] = var

    def save(self) -> None:
        data = {k: v.get().strip() for k, v in self.entries.items()}
        if data.get("ai_provider") not in PROVIDERS:
            self.msg.config(text="Invalid provider.", fg="#f87171")
            return
        try:
            data["timeout_ms"] = int(data.get("timeout_ms") or 30000)
            assert 1000 <= data["timeout_ms"] <= 120000
        except (ValueError, AssertionError):
            self.msg.config(text="Timeout must be 1000–120000 ms.", fg="#f87171")
            return
        # Never wipe stored secrets with an empty field the user didn't touch.
        current = load_settings()
        for key in ("groq_api_key", "gemini_api_key"):
            if not data.get(key):
                data[key] = getattr(current, key)
        try:
            save_user_settings(data)
            self.msg.config(text="✓ Saved. New popups use these settings.", fg="#4ade80")
        except Exception as e:
            self.msg.config(text=f"Save failed: {e}", fg="#f87171")

    def present(self) -> None:
        try:
            self.win.deiconify()
            self.win.lift()
            self.win.focus_force()
        except Exception:
            pass

    @classmethod
    def open(cls, master) -> "SettingsWindow":
        if cls._instance is None or not cls._instance.win.winfo_exists():
            cls._instance = cls(master)
        else:
            cls._instance.present()
        return cls._instance
