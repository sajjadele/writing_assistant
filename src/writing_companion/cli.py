"""Command-line interface and standard stream IPC handler (ADR-07 & contracts/ipc-protocol.md)."""

import sys
import json
import asyncio
import argparse
from typing import NoReturn

from writing_companion.config import load_settings
from writing_companion.core.schema import IPCRequest, IPCResponse, IPCError
from writing_companion.core.engine import Engine
from writing_companion.storage.sqlite_store import SQLiteStore


def build_engine() -> Engine:
    """Instantiate configured engine with local storage and providers."""
    settings = load_settings()
    store = SQLiteStore(settings.db_path)
    engine = Engine(settings, store)
    timeout_s = settings.timeout_ms / 1000.0

    # Conditionally register cloud/local providers if configured
    try:
        from writing_companion.providers.groq_provider import GroqProvider
        if settings.groq_api_key:
            engine.register_provider(GroqProvider(settings.groq_api_key, settings.groq_model, timeout_s))
    except ImportError:
        pass

    try:
        from writing_companion.providers.gemini_provider import GeminiProvider
        if settings.gemini_api_key:
            engine.register_provider(GeminiProvider(settings.gemini_api_key, settings.gemini_model, settings.proxy, timeout_s))
    except ImportError:
        pass

    try:
        from writing_companion.providers.ollama_provider import OllamaProvider
        engine.register_provider(OllamaProvider(settings.ollama_host, settings.ollama_model, timeout_s))
    except ImportError:
        pass

    return engine


def _emit_ipc(resp: IPCResponse) -> None:
    """Write one JSON line to stdout as UTF-8 bytes.

    Windows consoles default to cp1252; plain print() of Persian text
    raises "'charmap' codec can't encode". Writing bytes avoids it and
    keeps the IPC protocol byte-compatible on every OS.
    """
    payload = resp.model_dump_json(by_alias=True).encode("utf-8") + b"\n"
    try:
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()
    except Exception:
        # Fallback for captured/redirected streams without .buffer
        sys.stdout.write(resp.model_dump_json(by_alias=True) + "\n")
        sys.stdout.flush()


async def handle_ipc() -> None:
    """Read single JSON request from stdin and write JSON response to stdout."""
    try:
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        resp = IPCResponse(
            status="error",
            error=IPCError(code="EMPTY_INPUT", message="Standard input was empty."),
        )
        _emit_ipc(resp)
        return

    try:
        data = json.loads(raw_input)
        req = IPCRequest(**data)
    except Exception as e:
        resp = IPCResponse(
            status="error",
            error=IPCError(code="PARSE_ERROR", message=f"Invalid JSON payload: {e}"),
        )
        _emit_ipc(resp)
        return

    engine = build_engine()

    if req.action == "correct":
        if not req.text or not req.text.strip():
            resp = IPCResponse(
                status="error",
                error=IPCError(code="EMPTY_INPUT", message="Text field is required for correction."),
            )
            _emit_ipc(resp)
            return

        try:
            inference, event_id, backend_name, duration_ms = await engine.process_text(
                text=req.text,
                preferred_backend=req.preferred_backend,
            )
            resp = IPCResponse(
                status="success",
                data=inference,
                metadata={
                    "event_id": event_id,
                    "backend_used": backend_name,
                    "duration_ms": duration_ms,
                },
            )
            _emit_ipc(resp)
        except Exception as e:
            resp = IPCResponse(
                status="error",
                error=IPCError(code="EXECUTION_ERROR", message=str(e)),
            )
            _emit_ipc(resp)

    elif req.action == "log_feedback":
        if req.event_id is None or req.accepted is None:
            resp = IPCResponse(
                status="error",
                error=IPCError(
                    code="INVALID_ARGUMENTS",
                    message="event_id and accepted boolean are required.",
                ),
            )
            _emit_ipc(resp)
            return

        success = engine.update_feedback(event_id=req.event_id, accepted=req.accepted)
        resp = IPCResponse(
            status="success" if success else "error",
            metadata={"event_id": req.event_id, "accepted": req.accepted, "updated": success},
        )
        _emit_ipc(resp)


def main() -> None:
    """CLI entrypoint."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Writing Companion CLI & IPC service")
    parser.add_argument("--ipc", action="store_true", help="Run in JSON standard stream IPC mode")
    parser.add_argument("--dashboard", action="store_true", help="Launch Libadwaita desktop dashboard and settings GUI")
    parser.add_argument("--text", type=str, help="Evaluate text directly from CLI")
    args = parser.parse_args()

    if args.dashboard:
        from writing_companion.ui.dashboard import run_dashboard
        run_dashboard()
    elif args.ipc:
        asyncio.run(handle_ipc())
    elif args.text:
        engine = build_engine()
        result, event_id, backend, ms = asyncio.run(engine.process_text(args.text))
        print(f"\n[Backend: {backend} | {ms}ms | Event #{event_id}]")
        print(f"Correct: {result.is_correct}")
        print(f"Meaning (FA): {result.interpreted_meaning_fa}")
        print(f"Suggestion (EN): {result.corrected_text}")
        if result.changes:
            print("Changes:")
            for ch in result.changes:
                print(f"  - [{ch.category}] '{ch.original}' -> '{ch.replacement}': {ch.explanation_fa}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
