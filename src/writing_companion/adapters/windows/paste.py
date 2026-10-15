"""Emit Shift+Insert via Win32 keybd_event (ctypes only, no dependency).

Mirrors extension/keyboard.js::emitPaste after the ADR-09 standardisation.
"""

from __future__ import annotations

import ctypes
import time

VK_SHIFT = 0x10
VK_INSERT = 0x2D
KEYEVENTF_KEYUP = 0x0002


def _keybd(vk: int, press: bool) -> None:
    ctypes.windll.user32.keybd_event(vk, 0, 0 if press else KEYEVENTF_KEYUP, 0)


def emit_paste() -> bool:
    """Press Shift+Insert to paste clipboard over the selection."""
    try:
        _keybd(VK_SHIFT, True)
        time.sleep(0.025)
        _keybd(VK_INSERT, True)
        _keybd(VK_INSERT, False)
        time.sleep(0.025)
        _keybd(VK_SHIFT, False)
        return True
    except Exception:
        return False
