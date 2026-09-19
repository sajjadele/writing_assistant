<!--
Sync Impact Report:
- Version change: Uninitialized -> 1.0.0
- Initial ratification of Writing Assistant Constitution based on ADR-01 through ADR-07.
- Principles codified:
  1. Minimal Intervention & Technical Integrity (ADR-03)
  2. Semantic Checkpoint & Anti-Drift (ADR-02)
  3. Tolerance for Hybrid & Broken Inputs (ADR-01)
  4. Single-Inference Structured Contract (ADR-04)
  5. Local-First Privacy & Silent Learning (ADR-06)
  6. Decoupled Compositor-Level UI Architecture (ADR-07)
- Follow-up TODOs: None.
-->

# English Writing Companion Constitution

## Core Principles

### I. Minimal Intervention & Technical Integrity (NON-NEGOTIABLE)
The system MUST preserve the user's original phrasing, structure, and intent wherever possible, correcting only grammar, prepositions, and natural collocations without imposing arbitrary literary rewrites.
- Technical code identifiers (function names, variables, API routes, terminal flags, commands) MUST NEVER be modified or translated.
- If the user's input is already grammatically and idiomatically acceptable, the system MUST return `is_correct: true` ("No Change Needed") with a green checkmark rather than generating cosmetic revisions.

### II. Semantic Checkpoint & Anti-Drift (NON-NEGOTIABLE)
To protect technical users from catastrophic semantic drift when prompting AI agents or writing technical messages, the system MUST present its interpretation of the user's intent in Persian (`interpreted_meaning_fa`) before or alongside the suggested English text.
- The Persian interpretation MUST reflect raw user intent rather than a mechanical back-translation of the corrected English sentence.
- The interface acts as a passive guardrail: the user can verify semantic alignment with a single glance in under two seconds.

### III. Tolerance for Hybrid & Broken Inputs
The assistant is fundamentally an Expression Companion, not a punitive grammar tester. It MUST gracefully accept:
- Broken English and non-fluent phrasing.
- Persian-to-English cognitive syntax transfer patterns.
- Hybrid inputs with bracketed Persian bridge words (e.g., `Can we [سازگار کنیم] this?`), automatically converting them into standard natural English.

### IV. Single-Inference Structured JSON Contract
All correction attributes—grammatical validation, Persian semantic checkpoint, natural English expression, and micro-pedagogy diffs—MUST be acquired in a single API inference turn.
- Contract schema: `{ "is_correct": bool, "interpreted_meaning_fa": str, "corrected_text": str, "changes": [...] }`.
- Multi-turn chained prompts or sequential calls are strictly prohibited in the real-time writing loop to maintain response latencies under 500ms.

### V. Local-First Privacy & Silent Learning
User keystrokes, input texts, and correction history belong exclusively to the user and MUST NEVER be transmitted to external servers for tracking or telemetric profiling.
- Event records and user acceptance signals (`accepted: true` on Enter, `accepted: false` on Esc) MUST be stored strictly in a local SQLite database (`history.db`).
- Learning loop analytics run 100% locally to detect repeated user error patterns.

### VI. Decoupled Compositor-Level UI Architecture
The user interface MUST NOT disrupt or re-tile the user's active desktop environment.
- On Linux (Ubuntu / GNOME Wayland), the presentation layer MUST run as an in-compositor extension, anchored directly to mouse cursor coordinates (`global.get_pointer()`) and completely immune to tiling window managers (Pop-Shell).
- Core application logic (Prompt Engine, AI Adapters, SQLite Storage) MUST remain 100% pure Python and strictly decoupled from presentation adapters to ensure identical functionality when ported to Windows.

## Technical Standards & Performance Constraints

### Performance Benchmarks
- **Total Latency Budget**: Maximum 500ms end-to-end from shortcut press to rendered suggestion.
- **AI Provider Target**: Sub-300ms inference time (via high-throughput cloud providers like Groq / Gemini Flash, with local Ollama fallback).
- **UI Render Overhead**: Sub-20ms instant popup appearance.

### Technology Stack Constraints
- **Core Engine**: Python 3.11+, typed, modular hexagonal architecture.
- **Desktop Compositor Adapter**: GNOME 46 Shell Extension (ES Modules / GJS / Clutter / St).
- **Secondary Target**: Windows Win32 frameless native overlay.
- **Local Storage**: SQLite 3 with WAL mode enabled.

## Development Workflow & Quality Gates

### Spec-Driven Development (SDD) Mandatory Workflow
1. **Constitution Compliance**: Every proposed change must verify adherence to Principles I through VI.
2. **Phase Progression**: Features MUST progress through `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement` → `/speckit-converge`. Code MUST NOT be written without an approved task.
3. **Commit Standards**: All commits MUST follow Conventional Commits formatting (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`).
4. **Documentation Integrity**: Architectural decisions MUST be synchronized in `docs/03_DECISION_LOG.md` and `docs/02_CONTEXT_AND_EVOLUTION.md`.

## Governance

This Constitution represents the supreme architectural and product governing standard for the English Writing Companion repository. It supersedes all individual preferences, transient prompt suggestions, and informal conventions.
- Any amendment, removal, or addition of core principles requires formal documentation in the Architecture Decision Log (ADR) and explicit user ratification.
- Version increment rules:
  - **MAJOR**: Breaking removals or redefinitions of Core Principles.
  - **MINOR**: Addition of new principles, platforms, or technical governance sections.
  - **PATCH**: Clarifications, terminology refinements, and non-semantic typo corrections.

**Version**: 1.0.0 | **Ratified**: 2026-09-18 | **Last Amended**: 2026-09-19
