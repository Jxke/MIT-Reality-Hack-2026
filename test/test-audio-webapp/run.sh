#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8082

# Get a routable IP to print a useful URL
IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "=== mic-monitor web app ==="
echo "Requires bridge-shim to be running (arduino-app-cli app start user:bridge-shim)"
echo ""
echo "Open in browser: http://${IP}:${PORT}/"
echo ""

exec python3 "$SCRIPT_DIR/python/main.py"
