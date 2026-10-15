"""Windows clipboard + cursor helpers (stdlib + ctypes only)."""

from __future__ import annotations

import ctypes
from ctypes import wintypes


def get_cursor_pos() -> tuple[int, int]:
    """Return (x, y) via Win32 GetCursorPos; fallback to (500, 300)."""
    try:
        pt = wintypes.POINT()
        if ctypes.windll.user32.GetCursorPos(ctypes.byref(pt)):
            return int(pt.x), int(pt.y)
    except Exception:
        pass
    return (500, 300)


def get_clipboard_text() -> str:
    """Read text clipboard via tkinter (no extra dependency)."""
    try:
        import tkinter as tk
    except Exception:
        return ""
    try:
        root = tk.Tk()
        root.withdraw()
        try:
            text = root.clipboard_get()
        except Exception:
            text = ""
        root.destroy()
        return text.strip()
    except Exception:
        return ""


def set_clipboard_text(text: str) -> bool:
    """Write text to the Windows clipboard via tkinter."""
    try:
        import tkinter as tk
    except Exception:
        return False
    try:
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        root.destroy()
        return True
    except Exception:
        return False
