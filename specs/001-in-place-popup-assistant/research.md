# Phase 0 Research: In-Place Popup Architecture & Technical Decisions

**Feature**: `001-in-place-popup-assistant`  
**Date**: 2026-09-19  
**Status**: Completed

---

## 1. GNOME Shell Extension Popup Anchoring (Wayland / Mutter)

### Decision
Use a native GNOME Shell Extension (Mutter/Clutter Compositor level) to render the popup directly at `global.get_pointer()`.

### Rationale
- **Zero Tiling Conflicts**: Mutter only manages client windows (`MetaWindow`). An in-compositor UI element (`St.Widget` / `Clutter.Actor`) lives directly inside the compositor's scene graph (`Main.uiGroup`). Pop-Shell, i3, or other tiling window managers are technically incapable of tiling or resizing it.
- **Accurate In-Place Placement**: In Wayland, client applications are isolated and cannot query global cursor coordinates. GNOME Shell possesses native access to `global.get_pointer()` and can anchor the popup precisely next to the highlighted text.
- **Instant Activation**: The extension actor is already present in compositor memory; activation takes under 15ms with zero process spawning overhead.

### Alternatives Considered
- *Frameless GTK4 Window with Pop-Shell Float Exception*: Tested in Spike #1. Failed because Pop-Shell does not dynamically reload config on disk without restarting, and Wayland places unanchored top-level windows at (0, 0) top-left corner.
- *Layer-Shell Protocol (`wlr-layer-shell`)*: Not natively supported by GNOME's Mutter compositor without unofficial third-party patches.

---

## 2. IPC Protocol between GNOME Extension & Python Core

### Decision
Use lightweight asynchronous subprocess execution (`Gio.Subprocess`) with JSON over stdout/stdin for MVP, with upgrade path to a local Unix Domain Socket daemon.

### Rationale
- `Gio.Subprocess` is built directly into GJS/GLib without external dependencies.
- It executes asynchronously without blocking GNOME Shell's main rendering thread.
- Python startup overhead with standard libraries is ~30-40ms, well within our 500ms budget.
- Clean process isolation ensures that any Python crash will not destabilize the desktop session.

### Alternatives Considered
- *D-Bus Session Bus Service*: Highly robust, but requires registering a system D-Bus service file and daemon lifecycle management. Kept as an architectural evolution for later releases.
- *WebSockets / HTTP localhost*: Unnecessary network stack overhead and port collision risks on the user's machine.

---

## 3. High-Speed AI Engine & Latency Strategy

### Decision
Support a dual-provider adapter architecture:
1. **Primary Cloud Provider**: Groq API (`llama-3.3-70b-versatile`) or Gemini 1.5/2.0 Flash for sub-300ms inference.
2. **Local Fallback**: Local Ollama instance (`llama3.2` or `qwen2.5-coder`) for offline resilience.

### Rationale
- The real-time writing loop requires under 500ms total budget. Cloud inference via Groq or Gemini Flash reliably achieves 180ms–280ms Time-To-First-Token (TTFT).
- Single-Inference JSON contract guarantees only one network roundtrip per user interaction.

### Alternatives Considered
- *Local-only LLM*: While ideal for privacy, running 7B+ models locally on non-GPU hardware adds 2–4 seconds of latency, breaking the fluid writing loop.
- *Chained API calls (Translate then correct)*: Multiplying roundtrips adds 600ms+ latency and increases failure points.

---

## 4. In-Place Text Replacement (Auto-Paste)

### Decision
Implement automated text replacement using GNOME Shell's virtual input device (`Clutter.InputDeviceType.KEYBOARD_DEVICE`) to emit `Shift + Insert` immediately following clipboard update.

### Rationale
- Highlighting text in Linux applications already places it into the primary selection.
- When the user presses `Enter`, the extension sets both regular and primary clipboards, hides the popup, and emits `Shift + Insert` to paste into the active application.
- Tested and proven in `clipboard-indicator` (`keyboard.js`). Works uniformly across terminals, web browsers, and text editors.

### Alternatives Considered
- *`wtype` or `ydotool` external CLI tools*: Require root/uinput daemon configuration or custom Wayland compositor protocols.
- *Copy-only (Manual Ctrl+V)*: Rejected per user choice in Question 1; auto-paste provides a seamless zero-extra-click experience.

---

## 5. Local Persistence & Privacy (SQLite)

### Decision
Store all correction events in a local SQLite 3 database located at `~/.local/share/writing_companion/history.db` with Write-Ahead Logging (WAL) enabled.

### Rationale
- Single-file zero-configuration database built into Python standard library (`sqlite3`).
- WAL mode allows concurrent reads and rapid writes without locking.
- 100% local, satisfying Principle V of the Constitution.
