"""Windows clipboard + cursor helpers (stdlib + ctypes only).

Clipboard access reuses ONE long-lived hidden Tk root. Creating a fresh
``tk.Tk()`` per call spawns a new Tcl interpreter each time, which is both
wasteful and fatal if it ever happens re-entrantly inside a Win32 modal
loop (e.g. TrackPopupMenu) — observed as PyEval_RestoreThread crash.
All functions here must be called from the Tk (main) thread.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes


_shared_root = None


def _root():
    """Process-wide hidden root for clipboard ops (created once)."""
    global _shared_root
    try:
        if _shared_root is not None and _shared_root.winfo_exists():
            return _shared_root
    except Exception:
        pass
    import tkinter as tk

    _shared_root = tk.Tk()
    _shared_root.withdraw()
    return _shared_root


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
    """Read text clipboard via the shared hidden root (main thread only)."""
    try:
        root = _root()
        try:
            return root.clipboard_get().strip()
        except Exception:
            return ""
    except Exception:
        return ""


def set_clipboard_text(text: str) -> bool:
    """Write text to the Windows clipboard via the shared hidden root."""
    try:
        root = _root()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        return True
    except Exception:
        return False
