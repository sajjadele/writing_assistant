"""Global hotkey listener for Ctrl+Alt+G on Windows.

Prefers the ``keyboard`` package if installed; otherwise falls back to
``pynput``; if neither is available, raises a helpful error telling the
user what to install (``pip install keyboard``). A Tkinter-only fallback
cannot capture system-wide hotkeys, so we do not pretend otherwise.
"""

from __future__ import annotations

from typing import Callable


def listen_ctrl_alt_g(callback: Callable[[], None]) -> None:
    """Block forever, invoking callback on each Ctrl+Alt+G press."""
    # Option 1: `keyboard` package (simplest, no extra thread needed).
    try:
        import keyboard  # type: ignore

        keyboard.add_hotkey("ctrl+alt+g", callback)
        keyboard.wait()
        return
    except ImportError:
        pass
    except Exception as e:
        raise RuntimeError(f"keyboard listener failed: {e}") from e

    # Option 2: pynput.
    try:
        from pynput import keyboard as pk  # type: ignore

        pressed: set = set()

        def on_press(key):
            try:
                if key in (pk.Key.ctrl_l, pk.Key.ctrl_r):
                    pressed.add("ctrl")
                elif key in (pk.Key.alt_l, pk.Key.alt_r):
                    pressed.add("alt")
                elif getattr(key, "char", "") == "g":
                    if pressed == {"ctrl", "alt"}:
                        callback()
            except Exception:
                pass

        def on_release(key):
            try:
                if key in (pk.Key.ctrl_l, pk.Key.ctrl_r):
                    pressed.discard("ctrl")
                elif key in (pk.Key.alt_l, pk.Key.alt_r):
                    pressed.discard("alt")
            except Exception:
                pass

        with pk.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
        return
    except ImportError:
        pass

    raise RuntimeError(
        "No global-hotkey backend found. Install one with: pip install keyboard   (recommended) "
        "or: pip install pynput"
    )
