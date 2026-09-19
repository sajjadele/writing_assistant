# Quickstart Validation Guide: In-Place Popup Assistant

**Feature**: `001-in-place-popup-assistant`  
**Purpose**: Step-by-step verification guide to validate end-to-end functionality once implemented.

---

## 1. Prerequisites

- **OS**: Ubuntu 24.04 LTS (GNOME 46 Wayland Session)
- **Python**: 3.11 or newer (`python3 --version`)
- **GNOME Shell**: 46.x (`gnome-shell --version`)
- **API Key** (optional for mock, required for live LLM): `GROQ_API_KEY` or `GEMINI_API_KEY` in environment or `.env`

---

## 2. Environment Setup

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies (editable mode)
pip install -e ".[dev]"

# 3. Verify SQLite DB path initialization
python3 -c "import sqlite3, os; os.makedirs(os.path.expanduser('~/.local/share/writing_companion'), exist_ok=True)"
```

---

## 3. Core Engine CLI Validation (Mock & Live)

Verify that the Python core fulfills the [Single Inference JSON Contract](contracts/single-inference-json.json) and [IPC Protocol](contracts/ipc-protocol.md):

### Scenario A: Hybrid Text Correction with Bracketed Bridge Word
```bash
echo '{"action": "correct", "text": "Can we [سازگار کنیم] this function with new API?"}' | \
  python3 -m writing_companion.cli --ipc
```

**Expected Outcome**:
```json
{
  "status": "success",
  "data": {
    "is_correct": false,
    "interpreted_meaning_fa": "آیا می‌توانیم این تابع را با API جدید سازگار کنیم؟",
    "corrected_text": "Can we adapt this function to the new API?",
    "changes": [...]
  }
}
```

### Scenario B: Perfect Input (Minimal Intervention Check)
```bash
echo '{"action": "correct", "text": "This pull request resolves the memory leak."}' | \
  python3 -m writing_companion.cli --ipc
```

**Expected Outcome**:
`"is_correct": true`, `"corrected_text"` identical to original, no cosmetic rephrasings.

---

## 4. Local Database Validation

Verify that events are logged locally per [SQLite Schema](contracts/sqlite-schema.sql):

```bash
sqlite3 ~/.local/share/writing_companion/history.db "SELECT id, original_text, is_correct, accepted FROM correction_events ORDER BY id DESC LIMIT 1;"
```

**Expected Outcome**: A valid row reflecting the last executed query.

---

## 5. GNOME Shell Extension Validation (Desktop Integration)

### Step 1: Install Extension into Local User Profile
```bash
ln -s "$(pwd)/extension" ~/.local/share/gnome-shell/extensions/writing-assistant@sajjadele.github.com
gnome-extensions enable writing-assistant@sajjadele.github.com
```

### Step 2: In-Place Mouse Anchoring Test
1. Open any text editor (e.g., VS Code or Gedit) or terminal.
2. Type or select: `We should [بررسی کنیم] the latency bottleneck.`
3. Press global shortcut: `<Super>e` (or configured hotkey).
4. **Verification**:
   - The popup card appears instantly (<20ms) directly beside the mouse pointer.
   - Pop-Shell tiling manager **does not** tile or resize the window.
   - The Persian meaning ("💡 بررسی کنیم: We should investigate/examine...") is clearly readable.
5. Press `Enter`:
   - The selected text is automatically replaced in-place with the natural English sentence.
   - The popup closes smoothly.
