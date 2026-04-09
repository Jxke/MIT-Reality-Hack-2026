#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_SRC="$SCRIPT_DIR/../../test/test-audio-webapp/python/main.py"
APP_DEST="/home/arduino/ArduinoApps/mic-monitor/python/main.py"
PORT=8082

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: test-audio-webapp.sh"
  echo ""
  echo "Sync and run the mic-monitor web app (requires bridge-shim to be running)."
  echo "Open http://<board-ip>:${PORT}/ in a browser to listen to the microphone."
  echo ""
  echo "Options:"
  echo "  -h, --help  Show this help message"
  exit 0
fi

echo "=== Syncing mic-monitor app ==="
cp "$REPO_SRC" "$APP_DEST"
echo "Copied $(basename "$REPO_SRC") → $APP_DEST"

IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")
echo ""
echo "=== Starting mic-monitor web app ==="
echo "Open in browser: http://${IP}:${PORT}/"
echo "Press Ctrl-C to stop."
echo ""

exec python3 "$APP_DEST"
