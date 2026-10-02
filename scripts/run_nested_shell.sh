#!/usr/bin/env bash
# Run Writing Assistant inside an isolated Nested GNOME Shell
# Enables instant testing and hot-reloading without logging out or closing any host apps.

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXT_UUID="writing-assistant@sajjadele.github.com"
EXT_DIR="$HOME/.local/share/gnome-shell/extensions/$EXT_UUID"

echo "📦 Syncing latest extension files to $EXT_DIR..."
mkdir -p "$EXT_DIR"
cp -r "$PROJECT_DIR/extension/"* "$EXT_DIR/"

echo "========================================================"
echo "🚀 Launching Nested GNOME Shell (1280x800)..."
echo "💡 An isolated GNOME Shell window will open on your desktop."
echo "💡 Open any text app inside it, select text, and press Ctrl+Alt+G."
echo "💡 When you want to reload after code changes, simply close that"
echo "   window (or press Ctrl+C here) and run this script again!"
echo "========================================================"

dbus-run-session -- bash -c '
  (sleep 2 && gnome-extensions enable writing-assistant@sajjadele.github.com 2>/dev/null || true) &
  MUTTER_DEBUG_DUMMY_MODE_SPECS=1280x800 gnome-shell --nested --wayland
'
