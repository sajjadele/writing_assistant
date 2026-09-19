"""Integration tests for CLI standard stream IPC protocol (contracts/ipc-protocol.md)."""

import json
import subprocess
import sys
import pytest


def run_cli_ipc(payload: str) -> dict:
    """Run CLI in IPC mode with input payload via stdin and parse stdout JSON."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "writing_companion.cli", "--ipc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(input=payload)
    assert proc.returncode == 0, f"CLI exited with {proc.returncode}, stderr: {stderr}"
    return json.loads(stdout.strip())


def test_cli_ipc_correct_hybrid_input():
    payload = json.dumps({
        "action": "correct",
        "text": "Can we [سازگار کنیم] this function with new API?",
        "preferred_backend": "mock",
    })
    res = run_cli_ipc(payload)

    assert res["status"] == "success"
    assert res["data"]["is_correct"] is False
    assert "سازگار" in res["data"]["interpreted_meaning_fa"]
    assert "adapt" in res["data"]["corrected_text"]
    assert len(res["data"]["changes"]) > 0
    assert res["metadata"]["event_id"] > 0
    assert res["metadata"]["backend_used"] == "mock"


def test_cli_ipc_correct_perfect_input():
    payload = json.dumps({
        "action": "correct",
        "text": "This pull request resolves the memory leak.",
        "preferred_backend": "mock",
    })
    res = run_cli_ipc(payload)

    assert res["status"] == "success"
    assert res["data"]["is_correct"] is True
    assert res["data"]["corrected_text"] == "This pull request resolves the memory leak."
    assert res["data"]["changes"] == []


def test_cli_ipc_log_feedback():
    # First create an event
    create_payload = json.dumps({
        "action": "correct",
        "text": "Testing feedback loop.",
        "preferred_backend": "mock",
    })
    res1 = run_cli_ipc(create_payload)
    event_id = res1["metadata"]["event_id"]

    # Now update acceptance
    feedback_payload = json.dumps({
        "action": "log_feedback",
        "event_id": event_id,
        "accepted": True,
    })
    res2 = run_cli_ipc(feedback_payload)
    assert res2["status"] == "success"
    assert res2["metadata"]["event_id"] == event_id
    assert res2["metadata"]["accepted"] is True


def test_cli_ipc_empty_input():
    res = run_cli_ipc("")
    assert res["status"] == "error"
    assert res["error"]["code"] == "EMPTY_INPUT"


def test_cli_ipc_invalid_json():
    res = run_cli_ipc("{broken-json")
    assert res["status"] == "error"
    assert res["error"]["code"] == "PARSE_ERROR"
