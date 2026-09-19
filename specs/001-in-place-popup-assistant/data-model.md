# Data Model: In-Place Popup Expression Assistant

**Feature**: `001-in-place-popup-assistant`  
**Date**: 2026-09-19  
**Status**: Complete

---

## 1. Core Domain Entities

### `CorrectionEvent` (Persistent SQLite Entity)
Represents a recorded interaction cycle between the user, the AI engine, and the application.

| Field | Type | Description | Constraints |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | Unique event identifier | Primary Key, Auto Increment |
| `timestamp` | `TEXT` | UTC timestamp in ISO 8601 format | NOT NULL, Default `CURRENT_TIMESTAMP` |
| `original_text` | `TEXT` | Raw user input captured from selection | NOT NULL |
| `interpreted_meaning_fa` | `TEXT` | Extracted user intent in Persian | NULLABLE |
| `corrected_text` | `TEXT` | Natural English expression proposed by engine | NOT NULL |
| `is_correct` | `BOOLEAN` | True if original text was already acceptable | NOT NULL |
| `changes_json` | `TEXT` | JSON array of granular changes and micro-notes | NULLABLE |
| `accepted` | `BOOLEAN` | True if applied via Enter; False if dismissed | NOT NULL |
| `source_backend` | `TEXT` | Provider identifier (`groq`, `gemini`, `ollama`, `mock`) | NOT NULL |
| `duration_ms` | `INTEGER` | End-to-end execution latency in milliseconds | NULLABLE |

---

### `ChangeItem` (Value Object)
Granular breakdown of an individual modification within a sentence, used for educational feedback.

```json
{
  "original": "make this button in middle",
  "replacement": "center this button",
  "category": "word_choice",
  "explanation_fa": "در طراحی رابط کاربری از فعل center استفاده می‌شود."
}
```

Categories:
- `grammar`: Grammatical correction (tense, agreement, prepositions).
- `word_choice`: Contextually superior technical or natural vocabulary.
- `phrasing_idiom`: Restructuring awkward Persian-to-English cognitive syntax.
- `bracket_translation`: Resolving a Persian word enclosed in brackets `[واژه]`.

---

### `PopupSession` (Ephemeral UI State)
Represents the runtime state of the active GNOME Shell popup actor.

| Field | Type | Description |
| :--- | :--- | :--- |
| `pointer_x` | `Number` | Horizontal screen pixel coordinate of cursor |
| `pointer_y` | `Number` | Vertical screen pixel coordinate of cursor |
| `raw_text` | `String` | Raw captured text from primary selection |
| `state` | `Enum` | `IDLE`, `LOADING`, `SUCCESS`, `NO_CHANGE`, `ERROR` |
| `suggested_text` | `String` | Text ready for replacement |
| `active_actor` | `Clutter.Actor` | Reference to the current popup widget in scene graph |

---

## 2. State Lifecycle & Transitions

```
[Shortcut Triggered]
         │
         ▼
[Read Primary Selection] ──(empty)──► [Show Notification Toast] ──► [Exit]
         │
     (has text)
         ▼
[Anchor Actor at (x, y)]
         │
         ▼
[Show Loading State (<20ms)]
         │
         ▼
[Async Subprocess (Python Core Engine)]
         │
         ├──(success)──► [Render Suggested Card & Persian Meaning]
         │                       │
         │             ┌─────────┴─────────┐
         │             ▼                   ▼
         │      [Press Enter]         [Press Esc / Click Away]
         │             │                   │
         │      [Auto-Paste]          [Clean Dismissal]
         │      [Log accepted=1]      [Log accepted=0]
         │             │                   │
         │             └─────────┬─────────┘
         │                       ▼
         │                 [Close Actor]
         │
         └──(failure)──► [Show Graceful Error State] ──► [Dismiss]
```
