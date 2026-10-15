"""Windows orchestrator: hotkey -> clipboard -> core IPC -> Tkinter popup -> paste.

Usage:
    python -m writing_companion.adapters.windows.win_app --once --text "Can we [سازگار کنیم] this?"
    python -m writing_companion.adapters.windows.win_app --daemon   # Ctrl+Alt+G anywhere
"""

from __future__ import annotations

import argparse
import sys

from writing_companion.config import load_settings
from writing_companion.adapters.windows import ipc_client
from writing_companion.adapters.windows.clipboard_win import (
    get_clipboard_text,
    get_cursor_pos,
    set_clipboard_text,
)
from writing_companion.adapters.windows.paste import emit_paste


def _friendly_error(exc: Exception) -> str:
    """Map raw IPC/subprocess failures to a Persian user-facing message."""
    import subprocess as _sp

    if isinstance(exc, _sp.TimeoutExpired):
        return "⏳ پاسخ مدل طول کشید و زمان تمام شد. لطفاً با متن کوتاه‌تر دوباره تلاش کنید."
    msg = str(exc)
    if "timed out" in msg.lower():
        return "⏳ پاسخ مدل طول کشید و زمان تمام شد. لطفاً دوباره تلاش کنید."
    if "Proxy" in msg or "proxy" in msg or "ConnectError" in msg:
        return "🌐 اتصال به سرویس هوش مصنوعی برقرار نشد. اینترنت/VPN را بررسی کنید."
    return f"⚠️ خطا در پردازش متن: {msg[:200]}"


def process_once(text: str, preferred_backend: str = "auto") -> dict:
    """Run one correction through the core and return the raw IPC response."""
    settings = load_settings()
    timeout_s = settings.timeout_ms / 1000.0
    return ipc_client.correct_text(text, preferred_backend, timeout_s)


def show_popup_for_text(text: str, preferred_backend: str = "auto", master=None) -> None:
    """Full interactive flow with the Tkinter popup (Windows only).

    The popup appears instantly in loading state; the core IPC runs in a
    background thread and fills the fields when the result arrives.
    All tkinter calls stay on the calling (UI) thread.
    """
    import threading

    from writing_companion.adapters.windows.popup_win import WinPopup

    settings = load_settings()
    timeout_s = settings.timeout_ms / 1000.0
    cursor_x, cursor_y = get_cursor_pos()

    popup = WinPopup(cursor_x, cursor_y, master=master)
    popup.start_spinner()

    state: dict = {}
    holder: dict = {}

    def worker() -> None:
        try:
            state["res"] = ipc_client.correct_text(text, preferred_backend, timeout_s)
        except Exception as e:  # noqa: BLE001 - surfaced as friendly card
            state["err"] = e

    def render() -> None:
        """Main-thread render of the worker result (or re-poll)."""
        if getattr(popup, "_closed", True):
            return
        if "res" not in state and "err" not in state:
            try:
                popup.root.after(250, render)
            except Exception:
                pass
            return
        if "err" in state:
            popup.show_error(_friendly_error(state["err"]))
            return
        res = state["res"]
        if res.get("status") != "success":
            popup.show_error(res.get("error", {}).get("message", "Error processing text"))
            return
        data = res["data"]
        meta = res.get("metadata", {})
        holder["data"] = data
        holder["event_id"] = meta.get("event_id")
        backend = meta.get("backend_used", "AI")
        duration = meta.get("duration_ms", 0)
        badge = f"{backend} • {duration}ms"
        if data.get("is_correct"):
            popup.show_no_change(badge)
        else:
            popup.show_result(
                meaning_fa=data.get("interpreted_meaning_fa", ""),
                corrected=data.get("corrected_text", ""),
                changes=data.get("changes", []),
                badge=badge,
            )

    def accept() -> None:
        data = holder.get("data")
        if data is None:
            return  # still loading; popup queues it via _pending_accept
        print("[win] accepted -> clipboard + Shift+Insert", file=sys.stderr)
        if not data.get("is_correct"):
            set_clipboard_text(data.get("corrected_text", text))
            # Let focus return to the target app before pasting,
            # otherwise Shift+Insert lands nowhere.
            import time as _time

            _time.sleep(0.25)
            if not emit_paste():
                print("[win] paste failed: virtual keystroke rejected", file=sys.stderr)
        event_id = holder.get("event_id")
        if event_id:
            try:
                ipc_client.log_feedback(event_id, True, timeout_s)
            except Exception:
                pass

    def dismiss() -> None:
        print("[win] dismissed", file=sys.stderr)
        event_id = holder.get("event_id")
        if event_id:
            try:
                ipc_client.log_feedback(event_id, False, timeout_s)
            except Exception:
                pass

    def copy_only() -> None:
        data = holder.get("data")
        if data is None:
            return
        print("[win] copy-only -> clipboard", file=sys.stderr)
        set_clipboard_text(data.get("corrected_text", text))
        event_id = holder.get("event_id")
        if event_id:
            try:
                ipc_client.log_feedback(event_id, True, timeout_s)
            except Exception:
                pass

    threading.Thread(target=worker, daemon=True).start()
    try:
        popup.root.after(250, render)
    except Exception:
        pass
    popup.run_modal(on_accept=accept, on_dismiss=dismiss, on_copy=copy_only)


def run_daemon(preferred_backend: str = "auto") -> int:
    """Listen for Ctrl+Alt+G and process the clipboard text each time.

    The hidden Tk root lives in the main thread; hotkey callbacks only
    enqueue activations (tkinter is not thread-safe).
    """
    import queue
    import tkinter as tk

    try:
        from writing_companion.adapters.windows.hotkey import register_ctrl_alt_g
    except Exception as e:
        print(f"Hotkey backend unavailable: {e}", file=sys.stderr)
        return 1

    activations: queue.Queue = queue.Queue()
    root = tk.Tk()
    root.withdraw()

    poll = _make_poll(root, activations, preferred_backend)

    try:
        cleanup = register_ctrl_alt_g(lambda: activations.put("go"))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1

    print("Writing Assistant (Windows) listening on Ctrl+Alt+G. Press Ctrl+C to stop.")
    root.after(200, poll)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            cleanup()
        except Exception:
            pass
    return 0


def _make_poll(root, activations, preferred_backend, extra=None):
    """Shared activation consumer: clipboard -> popup (main thread only)."""
    import queue as _queue

    def poll() -> None:
        while True:
            try:
                activations.get_nowait()
            except _queue.Empty:
                break
            text = get_clipboard_text()
            if not text:
                print("Clipboard is empty: copy/select text first.")
                continue
            try:
                show_popup_for_text(text, preferred_backend, master=root)
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
        if extra is not None:
            try:
                extra()
            except Exception:
                pass
        root.after(200, poll)

    return poll


def run_tray(preferred_backend: str = "auto") -> int:
    """Resident tray controller: hotkey service + tray menu + windows.

    Single process owns everything (hotkey listener, hidden Tk root, tray
    icon, history/settings windows). The tray menu can pause/resume the
    hotkey service without killing the process.
    """
    import queue
    import tkinter as tk

    try:
        from writing_companion.adapters.windows.hotkey import register_ctrl_alt_g
    except Exception as e:
        print(f"Hotkey backend unavailable: {e}", file=sys.stderr)
        return 1
    try:
        from writing_companion.adapters.windows.tray import WinTray
        from writing_companion.adapters.windows.history_win import HistoryWindow
        from writing_companion.adapters.windows.settings_win import SettingsWindow
    except Exception as e:
        print(f"Tray UI unavailable: {e}", file=sys.stderr)
        return 1

    def drain_tray_actions() -> None:
        """Run menu actions requested by the native tray callback (main thread)."""
        while True:
            try:
                action = tray_actions.get_nowait()
            except queue.Empty:
                break
            try:
                if action == "toggle":
                    toggle()
                elif action == "history":
                    HistoryWindow.open(root)
                elif action == "settings":
                    SettingsWindow.open(root)
                elif action == "quit":
                    do_quit()
            except Exception as e:
                print(f"Tray action failed: {e}", file=sys.stderr)

    activations: queue.Queue = queue.Queue()
    tray_actions: queue.Queue = queue.Queue()
    root = tk.Tk()
    root.withdraw()
    poll = _make_poll(root, activations, preferred_backend, extra=drain_tray_actions)

    state = {"cleanup": None, "tray": None}

    def is_running() -> bool:
        return state["cleanup"] is not None

    def start_service() -> None:
        if state["cleanup"] is None:
            try:
                state["cleanup"] = register_ctrl_alt_g(lambda: activations.put("go"))
                print("Service started: listening on Ctrl+Alt+G.")
            except RuntimeError as e:
                print(str(e), file=sys.stderr)
                return
        _sync_tip()

    def stop_service() -> None:
        if state["cleanup"] is not None:
            try:
                state["cleanup"]()
            except Exception:
                pass
            state["cleanup"] = None
            print("Service paused.")
        _sync_tip()

    def toggle() -> None:
        stop_service() if is_running() else start_service()

    def _sync_tip() -> None:
        try:
            if state["tray"] is not None:
                state["tray"].refresh_tip(is_running())
        except Exception:
            pass

    def do_quit() -> None:
        stop_service()
        try:
            if state["tray"] is not None:
                state["tray"].remove()
        except Exception:
            pass
        try:
            root.quit()
            root.destroy()
        except Exception:
            pass

    try:
        state["tray"] = WinTray(
            sink=tray_actions.put_nowait,
            is_running=is_running,
        )
    except Exception as e:
        print(f"Could not create tray icon: {e}", file=sys.stderr)
        return 1

    start_service()
    root.after(200, poll)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        do_quit()
    return 0


def main(argv: list | None = None) -> int:
    import faulthandler

    try:
        faulthandler.enable()  # Python-level traceback on any future fatal crash
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Writing Assistant Windows adapter (Tkinter)")
    parser.add_argument("--once", action="store_true", help="Process one --text and print IPC JSON (no GUI)")
    parser.add_argument("--popup", action="store_true", help="Process one --text with the Tkinter popup")
    parser.add_argument("--daemon", action="store_true", help="Listen for Ctrl+Alt+G globally (headless)")
    parser.add_argument("--tray", action="store_true", help="Resident tray controller (service + history + settings)")
    parser.add_argument("--text", type=str, default="", help="Input text for --once/--popup")
    parser.add_argument("--from-clipboard", action="store_true", help="Wait for clipboard text then show popup")
    parser.add_argument("--wait", type=int, default=60, help="Seconds to wait for clipboard (default 60)")
    parser.add_argument("--backend", type=str, default="auto", help="Preferred backend")
    args = parser.parse_args(argv)

    if args.once:
        if not args.text.strip():
            print("Empty --text", file=sys.stderr)
            return 2
        import json

        out = json.dumps(process_once(args.text.strip(), args.backend), ensure_ascii=False, indent=2)
        try:
            sys.stdout.buffer.write(out.encode("utf-8") + b"\n")
            sys.stdout.buffer.flush()
        except Exception:
            print(out)
        return 0
    if args.popup:
        if not args.text.strip():
            print("Empty --text", file=sys.stderr)
            return 2
        show_popup_for_text(args.text.strip(), args.backend)
        return 0
    if args.from_clipboard:
        import time as _time

        text = get_clipboard_text()
        for _ in range(max(1, args.wait)):
            if text:
                break
            _time.sleep(1)
            text = get_clipboard_text()
        if not text:
            print("Clipboard is empty: copy/select text first.", file=sys.stderr)
            return 2
        show_popup_for_text(text, args.backend)
        return 0
    if args.daemon:
        return run_daemon(args.backend)
    if args.tray:
        return run_tray(args.backend)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
