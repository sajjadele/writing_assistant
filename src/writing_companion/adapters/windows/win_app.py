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


def process_once(text: str, preferred_backend: str = "auto") -> dict:
    """Run one correction through the core and return the raw IPC response."""
    settings = load_settings()
    timeout_s = settings.timeout_ms / 1000.0
    return ipc_client.correct_text(text, preferred_backend, timeout_s)


def show_popup_for_text(text: str, preferred_backend: str = "auto") -> None:
    """Full interactive flow with the Tkinter popup (Windows only)."""
    from writing_companion.adapters.windows.popup_win import WinPopup

    settings = load_settings()
    timeout_s = settings.timeout_ms / 1000.0
    cursor_x, cursor_y = get_cursor_pos()

    popup = WinPopup(cursor_x, cursor_y)
    try:
        res = ipc_client.correct_text(text, preferred_backend, timeout_s)
    except Exception as e:
        popup.show_error(str(e))
        popup.run_modal(on_accept=lambda: None, on_dismiss=lambda: None)
        return

    if res.get("status") != "success":
        popup.show_error(res.get("error", {}).get("message", "Error processing text"))
        popup.run_modal(on_accept=lambda: None, on_dismiss=lambda: None)
        return

    data = res["data"]
    meta = res.get("metadata", {})
    event_id = meta.get("event_id")
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

    corrected = data.get("corrected_text", text)

    def accept() -> None:
        if not data.get("is_correct"):
            set_clipboard_text(corrected)
            emit_paste()
        if event_id:
            try:
                ipc_client.log_feedback(event_id, True, timeout_s)
            except Exception:
                pass

    def dismiss() -> None:
        if event_id:
            try:
                ipc_client.log_feedback(event_id, False, timeout_s)
            except Exception:
                pass

    def copy_only() -> None:
        set_clipboard_text(corrected)
        if event_id:
            try:
                ipc_client.log_feedback(event_id, True, timeout_s)
            except Exception:
                pass

    popup.run_modal(on_accept=accept, on_dismiss=dismiss, on_copy=copy_only)


def run_daemon(preferred_backend: str = "auto") -> int:
    """Listen for Ctrl+Alt+G and process the clipboard text each time."""
    from writing_companion.adapters.windows.hotkey import listen_ctrl_alt_g

    print("Writing Assistant (Windows) listening on Ctrl+Alt+G. Press Ctrl+C to stop.")

    def on_hotkey() -> None:
        text = get_clipboard_text()
        if not text:
            print("Clipboard is empty: copy/select text first.")
            return
        try:
            show_popup_for_text(text, preferred_backend)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

    try:
        listen_ctrl_alt_g(on_hotkey)
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Writing Assistant Windows adapter (Tkinter)")
    parser.add_argument("--once", action="store_true", help="Process one --text and print IPC JSON (no GUI)")
    parser.add_argument("--popup", action="store_true", help="Process one --text with the Tkinter popup")
    parser.add_argument("--daemon", action="store_true", help="Listen for Ctrl+Alt+G globally")
    parser.add_argument("--text", type=str, default="", help="Input text for --once/--popup")
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
    if args.daemon:
        return run_daemon(args.backend)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
