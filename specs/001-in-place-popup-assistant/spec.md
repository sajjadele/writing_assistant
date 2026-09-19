# Feature Specification: In-Place Popup Expression Assistant

**Feature Branch**: `001-in-place-popup-assistant`

**Created**: 2026-09-19

**Status**: Draft

**Input**: User description: "In-place popup expression companion that appears directly next to the active text selection/cursor without disturbing or tiling background windows, displaying natural English suggestions and a Persian semantic checkpoint."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Contextual In-Place Popup & Natural Expression (Priority: P1)

As a user writing English in any desktop application (IDE, browser, chat, terminal), I want to highlight my drafted sentence and trigger a global shortcut so that a compact, frameless popup card appears directly adjacent to my selected text without resizing, splitting, or tiling my active workspace, displaying a natural English correction alongside a Persian explanation of my intent.

**Why this priority**: This is the core MVP loop (`Select → Understand → Replace`). Without an in-place popup that respects the user's tiling window manager, the product disrupts workflow and fails its primary value proposition.

**Independent Test**: Can be verified by highlighting draft text in any editor, pressing the global shortcut, confirming the popup appears at the cursor location without disturbing window layouts, and pressing `Enter` to apply the text.

**Acceptance Scenarios**:

1. **Given** text is highlighted in an active application window, **When** the user presses `Ctrl + Alt + G`, **Then** a compact popup opens immediately next to the cursor/selection coordinates, leaving all surrounding application windows completely undisturbed.
2. **Given** the popup is displayed, **When** the user presses `Enter`, **Then** the suggested English text replaces the highlighted selection in the active app and the popup cleanly closes.
3. **Given** the popup is displayed, **When** the user presses `Esc` or clicks anywhere outside the popup card, **Then** the popup instantly dismisses with zero changes made to the text.

---

### User Story 2 - Semantic Anti-Drift Guardrail & Technical Integrity (Priority: P2)

As a technical user writing prompts for AI coding agents or communicating with colleagues, I want to see a clear Persian statement of how the system understood my sentence before applying it, so that I can prevent semantic drift and ensure code identifiers are preserved untouched.

**Why this priority**: Technical users fear that automated rewriting will alter function names, API endpoints, or invert logical instructions. The Persian semantic checkpoint provides instantaneous confidence within two seconds.

**Independent Test**: Can be tested by drafting sentences with hybrid Persian bracketed words (e.g. `Can we [سازگار کنیم] this?`) or broken technical phrases, verifying that the Persian checkpoint accurately reflects the raw intent and that code symbols remain unaltered.

**Acceptance Scenarios**:

1. **Given** the user inputs a sentence containing technical code identifiers (e.g. `center button without break layout`), **When** the popup renders, **Then** code terms remain intact, the suggestion is grammatically natural, and the Persian checkpoint describes the functional meaning accurately.
2. **Given** the user inputs a hybrid phrase with a bracketed Persian word (e.g. `Can we [سازگار کنیم] this?`), **When** the popup renders, **Then** the bracketed word is converted to the appropriate English equivalent (`compatible with`) and explained in Persian.
3. **Given** the user inputs text that is already grammatically and idiomatically sound, **When** the popup renders, **Then** the system displays a "No Change Needed" green confirmation without generating cosmetic rewrites.

---

### User Story 3 - Local Privacy & Learning History (Priority: P3)

As a privacy-focused professional, I want all my writing corrections and acceptance decisions to be stored strictly in a private local database on my machine, so that no sensitive communication is transmitted to telemetry servers and the system can build a local learning profile over time.

**Why this priority**: Builds the foundation for Milestone 2 (personalized error pattern detection) while ensuring zero telemetry leakage of user typing habits.

**Independent Test**: Can be tested by accepting several suggestions and dismissing others, then inspecting the local SQLite database to confirm event records accurately capture timestamp, original text, suggested text, and acceptance status.

**Acceptance Scenarios**:

1. **Given** a suggestion is accepted via `Enter`, **When** the popup closes, **Then** a record is saved to the local database with `accepted: true`.
2. **Given** a suggestion is dismissed via `Esc` or loss of focus, **When** the popup closes, **Then** a record is saved to the local database with `accepted: false`.

---

### Edge Cases

- **Empty Selection**: What happens when the user triggers the shortcut without highlighting any text? [NEEDS CLARIFICATION: Should an inline input field appear within the popup for direct typing, or should a brief system notification prompt the user to select text?]
- **Application Replacement Method**: How should the system deliver the corrected text to the target application on Enter? [NEEDS CLARIFICATION: Should the system simulate automatic paste (Shift+Insert/Ctrl+V) directly into the target field, or copy to the clipboard for manual pasting?]
- **Network or AI Latency Spike**: If the AI inference takes longer than 500ms, the popup MUST display a subtle loading/thinking state rather than leaving the user uncertain.
- **Very Long Selection**: When highlighted text exceeds 800 characters, the popup card MUST support internal smooth scrolling rather than expanding beyond the viewport.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST register a global shortcut (`Ctrl + Alt + G`) that triggers the assistant from any active desktop window.
- **FR-002**: System MUST capture highlighted text from the operating system's primary selection upon shortcut activation.
- **FR-003**: System MUST display an in-place floating popup card positioned adjacent to the active cursor/selection coordinates (`global.get_pointer()`).
- **FR-004**: System MUST NOT allow the popup to be tiled, docked, or resized by tiling window managers (Pop-Shell).
- **FR-005**: System MUST present a natural, fluent English correction that adheres to the Minimal Intervention principle.
- **FR-006**: System MUST present a Persian semantic interpretation (`interpreted_meaning_fa`) reflecting the user's intended meaning.
- **FR-007**: System MUST preserve all code identifiers, variable names, terminal commands, and API routes without modification.
- **FR-008**: System MUST support hybrid inputs with Persian words placed inside brackets (e.g. `[لغت]`).
- **FR-009**: System MUST display a "No Change Needed" status when the input text requires no correction.
- **FR-010**: System MUST dismiss the popup and apply the replacement when the `Enter` key is pressed.
- **FR-011**: System MUST dismiss the popup without modifying text when the `Esc` key is pressed or when focus leaves the popup card.
- **FR-012**: System MUST persist every interaction event (original text, correction, Persian checkpoint, acceptance boolean) into a private local SQLite database.

### Key Entities

- **Correction Event**: Represents an interaction cycle. Attributes: timestamp, original_text, interpreted_meaning_fa, corrected_text, changes_breakdown, accepted (boolean), provider_source.
- **Popup Session**: Ephemeral presentation state. Attributes: screen coordinates (x, y), raw input text, loading state, display card widgets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Popup appears in under 20ms from shortcut press without inducing window re-tiling or layout shifts.
- **SC-002**: End-to-end response time (from shortcut trigger to full rendering of suggestion and Persian checkpoint) is under 500ms in 95% of standard queries.
- **SC-003**: 100% of user interactions (both accepted and cancelled) are recorded locally with zero external network telemetry.
- **SC-004**: 0% rate of altered code identifiers (variables, functions, API paths) in technical inputs.
- **SC-005**: User can complete the entire inspection and replacement cycle with a single keyboard press (`Enter`).

## Assumptions

- Target operating environment for Phase 1 is Ubuntu 24.04 LTS running GNOME 46 under Wayland with Pop-Shell tiling enabled.
- Future desktop platforms (Windows 10/11) will reuse the identical Python core engine through a platform-specific Win32 presentation adapter.
- The user has configured an API key for high-speed cloud inference (Groq / Gemini Flash) or has a running local model (Ollama).
