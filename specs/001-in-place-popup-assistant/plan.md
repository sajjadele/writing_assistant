# Implementation Plan: In-Place Popup Expression Assistant

**Branch**: `main` | **Date**: 2026-09-19 | **Spec**: [Feature Specification](spec.md)

**Input**: Feature specification from `specs/001-in-place-popup-assistant/spec.md`

---

## Summary

The In-Place Popup Expression Assistant provides a seamless, system-wide writing and learning companion on Ubuntu 24.04 (Wayland / GNOME 46 / Pop-Shell). By running the presentation layer directly inside the GNOME Shell compositor (`St.Widget` / `Clutter.Actor`), the UI anchors precisely beside the mouse pointer (`global.get_pointer()`) and is completely immune to Pop-Shell window tiling. The Python Core engine evaluates text selection via a single-inference JSON contract, offering minimal grammatical fixes, Persian intent verification (Anti-Drift Semantic Checkpoint), in-place auto-replacement (`Shift + Insert` on Enter), and zero-telemetry local SQLite persistence.

---

## Technical Context

**Language/Version**: Python 3.11+ (Core Backend) & JavaScript / GJS ES Modules (GNOME 46 Shell Extension)  
**Primary Dependencies**: 
- Backend: Standard library (`sqlite3`, `json`, `subprocess`, `urllib`), optional lightweight SDKs (`httpx`, `groq`, `google-genai`)
- Frontend: GNOME Shell GJS native libraries (`Gio`, `Clutter`, `St`, `GLib`, `Meta`)  
**Storage**: Local SQLite 3 (`~/.local/share/writing_companion/history.db`) with Write-Ahead Logging (WAL)  
**Testing**: `pytest` for unit, contract, and IPC CLI validation  
**Target Platform**: Ubuntu 24.04 LTS (GNOME 46 Wayland with Pop-Shell Tiling), with decoupled architecture enabling Windows Win32 native overlay in future phases  
**Project Type**: System-wide desktop assistant (Hexagonal decoupled CLI / Subprocess service + Compositor UI extension)  
**Performance Goals**:
- UI popup render & anchoring: <20ms
- AI Provider Time-To-First-Token: <300ms
- Total end-to-end user loop (Hotkey to rendered card): <500ms  
**Constraints**:
- Absolute zero Pop-Shell tiling disruption
- Local-first privacy (no remote telemetric tracking)
- Strict single API roundtrip per interaction
- Technical code identifiers and commands must remain strictly untouched  
**Scale/Scope**: Single-user local desktop companion (~600 LOC Python Core, ~350 LOC GJS extension)

---

## Constitution Check

*GATE: All principles from `.specify/memory/constitution.md` verified.*

| Principle | Status | Justification & Safeguards |
| :--- | :--- | :--- |
| **I. Minimal Intervention** | **PASS** | Evaluated in prompt design and contract: `is_correct: true` triggers a green checkmark with zero cosmetic changes; code/technical identifiers are protected via strict prompt guardrails. |
| **II. Semantic Checkpoint** | **PASS** | The `interpreted_meaning_fa` field is mandatory in the single-inference JSON contract, giving users an instant 2-second intent verification in Persian. |
| **III. Hybrid & Broken Input** | **PASS** | Prompt and schema explicitly support non-fluent English and bracketed Persian bridge words (`[واژه]`), resolving them into fluent English. |
| **IV. Single-Inference JSON** | **PASS** | All attributes (`is_correct`, `interpreted_meaning_fa`, `corrected_text`, `changes`) are retrieved in a single structured LLM call under 300ms. Multi-turn chains are prohibited. |
| **V. Local-First Privacy** | **PASS** | All event logs and acceptance feedback are stored strictly in local SQLite (`history.db`). No telemetry or remote user data transmission. |
| **VI. Decoupled Compositor UI** | **PASS** | Clean hexagonal boundary: Presentation is an in-compositor GNOME extension; Core logic is 100% pure Python CLI/library, easily reusable across OS environments. |

---

## Project Structure

### Documentation (`specs/001-in-place-popup-assistant/`)

```text
specs/001-in-place-popup-assistant/
├── plan.md              # Implementation plan (this document)
├── research.md          # Phase 0 technical research & platform decisions
├── data-model.md        # Phase 1 entities, data model & UI lifecycle
├── quickstart.md        # Phase 1 manual validation scenarios
├── contracts/           # Phase 1 interfaces & schemas
│   ├── single-inference-json.json  # JSON schema for LLM response
│   ├── sqlite-schema.sql           # DDL for local history DB
│   └── ipc-protocol.md             # Extension <-> Python IPC specification
└── checklists/
    └── requirements.md  # 100% validated requirements checklist
```

### Source Code (`src/` and `extension/`)

```text
writing_assistant/
├── src/
│   └── writing_companion/
│       ├── __init__.py
│       ├── cli.py                  # IPC entrypoint for GNOME Shell extension
│       ├── config.py               # Settings (API keys, provider choice, paths)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── engine.py           # Core orchestrator
│       │   ├── prompt.py           # Single-inference prompt templates
│       │   └── schema.py           # Data structures & JSON validation
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py             # Abstract LLM provider interface
│       │   ├── groq_provider.py    # Primary cloud provider (Llama 3.3 70B)
│       │   ├── gemini_provider.py  # Alternative cloud provider (Flash 2.0)
│       │   ├── ollama_provider.py  # Local fallback provider
│       │   └── mock_provider.py    # Offline fixture provider for testing
│       └── storage/
│           ├── __init__.py
│           └── sqlite_store.py     # Local SQLite 3 WAL event repository
│
├── extension/                      # GNOME 46 Shell Extension
│   ├── metadata.json               # Extension metadata & UUID
│   ├── extension.js                # Lifecycle, shortcut capture, IPC manager
│   ├── popup.js                    # In-compositor St.Widget floating card
│   ├── keyboard.js                 # Virtual Clutter device for auto-paste
│   └── stylesheet.css              # Custom styling matching dark desktop theme
│
└── tests/
    ├── unit/
    │   ├── test_prompt.py          # Prompt formatting tests
    │   ├── test_schema.py          # JSON contract validation tests
    │   └── test_storage.py         # SQLite WAL persistence tests
    └── integration/
        └── test_cli_ipc.py         # Subprocess stdin/stdout IPC test
```

**Structure Decision**: Hexagonal modular architecture separating the core Python service (`src/writing_companion/`) from the Wayland presentation layer (`extension/`). This ensures full independence of business logic, effortless automated testing, and readiness for future Windows Win32 adapters.

---

## Complexity Tracking

> **Constitution Check**: Passed with ZERO violations. No unnecessary complexity introduced.
