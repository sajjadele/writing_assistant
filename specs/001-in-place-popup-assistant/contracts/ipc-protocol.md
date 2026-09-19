# IPC Protocol Specification: GNOME Shell Extension ⟷ Python Core

**Feature**: `001-in-place-popup-assistant`  
**Version**: 1.0.0  
**Transport**: Subprocess Standard Streams (`stdin` / `stdout` via `Gio.Subprocess`)  
**Format**: UTF-8 Encoded JSON

---

## 1. Overview & Architecture

To preserve clean hexagonal separation (Constitution Principle VI):
- The **GNOME Shell Extension** acts as a stateless presentation client handling keyboard capture, mouse cursor anchoring (`global.get_pointer()`), UI rendering (`St.Widget`), and auto-paste (`Shift + Insert`).
- The **Python Core Runner** encapsulates prompt orchestration, LLM provider communication (Groq/Gemini/Ollama), JSON contract validation, and local SQLite persistence.

Communication occurs asynchronously using non-blocking GLib subprocess calls (`Gio.Subprocess`) with strict timeout enforcement.

---

## 2. Command Invocation

The extension invokes the Python core CLI:
```bash
python3 -m writing_companion.cli --ipc
```

Input is piped via standard input (`stdin`) and the result is read from standard output (`stdout`).

---

## 3. Request Payloads

### 3.1 Correction Request (`correct`)
Sent immediately when user triggers the shortcut and highlighted text is captured.

```json
{
  "action": "correct",
  "text": "Can we [سازگار کنیم] this function with new API?",
  "preferred_backend": "auto"
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `action` | `string` | Must be `"correct"`. |
| `text` | `string` | Selected text (1 to 2000 characters). |
| `preferred_backend` | `string` | `"auto"`, `"groq"`, `"gemini"`, or `"ollama"`. Default: `"auto"`. |

---

### 3.2 Feedback / Acceptance Update (`log_feedback`)
Sent when user resolves the popup (via `Enter` to accept or `Esc`/Click-away to dismiss).

```json
{
  "action": "log_feedback",
  "event_id": 105,
  "accepted": true
}
```

| Field | Type | Description |
| :--- | :--- | :--- |
| `action` | `string` | Must be `"log_feedback"`. |
| `event_id` | `integer` | ID returned in previous correction response metadata. |
| `accepted` | `boolean` | `true` if replaced via Enter; `false` if dismissed without pasting. |

---

## 4. Response Payloads

### 4.1 Success Response (`correct`)
Returned with exit code `0` on standard output:

```json
{
  "status": "success",
  "data": {
    "is_correct": false,
    "interpreted_meaning_fa": "آیا می‌توانیم این تابع را با API جدید سازگار کنیم؟",
    "corrected_text": "Can we adapt this function to the new API?",
    "changes": [
      {
        "original": "[سازگار کنیم]",
        "replacement": "adapt",
        "category": "bracket_translation",
        "explanation_fa": "معادل مناسب فنی در زمینه هماهنگ‌سازی کدها."
      },
      {
        "original": "with new",
        "replacement": "to the new",
        "category": "grammar",
        "explanation_fa": "حرف اضافه مناسب برای فعل adapt در این بافت to است."
      }
    ]
  },
  "metadata": {
    "event_id": 105,
    "backend_used": "groq:llama-3.3-70b-versatile",
    "duration_ms": 235
  }
}
```

---

### 4.2 Error Response
Returned on API error, network failure, or parse failure:

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "AI Provider rate limit reached. Retrying or fallback to local model.",
    "is_transient": true
  },
  "metadata": {
    "backend_used": "groq",
    "duration_ms": 120
  }
}
```

Standard Error Codes:
- `EMPTY_INPUT`: No text provided to process.
- `TIMEOUT`: LLM provider did not answer within 4000ms.
- `RATE_LIMIT_EXCEEDED`: API quota reached.
- `PROVIDER_UNAVAILABLE`: Network offline and local Ollama unreachable.
- `PARSE_ERROR`: Provider output did not conform to JSON contract.

---

## 5. Timing & Timeout Contract
- **Maximum Extension Subprocess Timeout**: 4500ms.
- If the Python subprocess exceeds 4500ms, the extension aborts the process (`Gio.Subprocess.force_exit()`), shows a transient warning indicator, and gracefully dismisses.
