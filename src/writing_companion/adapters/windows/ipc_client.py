"""Blocking IPC client: talk to the core via ``python -m writing_companion.cli --ipc``.

Uses the same JSON contract as the GNOME extension
(specs/001-in-place-popup-assistant/contracts/ipc-protocol.md).
Timeout comes from Settings.timeout_ms (unified 7s).
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import Any


def run_ipc(payload: dict[str, Any], timeout_s: float = 30.0) -> dict[str, Any]:
    """Send one JSON request on stdin, parse one JSON response from stdout."""
    proc = subprocess.run(
        [sys.executable, "-m", "writing_companion.cli", "--ipc"],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        # Generous margin over the provider cap: interpreter startup +
        # engine overhead also consume wall-clock inside the subprocess.
        timeout=timeout_s + 10.0,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Core IPC exited {proc.returncode}: {proc.stderr.strip()[:500]}")
    return json.loads(proc.stdout.strip())


def correct_text(text: str, preferred_backend: str = "auto", timeout_s: float = 30.0) -> dict[str, Any]:
    return run_ipc({"action": "correct", "text": text, "preferred_backend": preferred_backend}, timeout_s)


def log_feedback(event_id: int, accepted: bool, timeout_s: float = 30.0) -> dict[str, Any]:
    return run_ipc({"action": "log_feedback", "event_id": event_id, "accepted": accepted}, timeout_s)
