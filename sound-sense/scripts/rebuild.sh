#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || -z "${1:-}" ]]; then
  echo "Usage: rebuild.sh <service>"
  echo ""
  echo "Rebuild and restart a single container."
  echo ""
  echo "Services:"
  podman-compose config --services 2>/dev/null || echo "  (run from project dir to list services)"
  echo ""
  echo "Options:"
  echo "  -h, --help  Show this help message"
  exit 0
fi

SERVICE="$1"

echo "=== Checking MCU health ==="
if nc -w 4 localhost 7500 2>/dev/null | grep -q "Audio packet sent"; then
  echo "MCU OK — audio packets flowing."
else
  echo ""
  echo "WARNING: No audio packets seen on port 7500."
  echo "The MCU sketch may have halted. A full power cycle of the board is required."
  echo "Press Enter to continue anyway, or Ctrl-C to abort."
  read -r
fi

if [[ "$SERVICE" == "pipeline" ]]; then
  echo "=== Syncing and restarting bridge shim ==="
  cp "$SCRIPT_DIR/../mcu/bridge_shim.py" /home/arduino/ArduinoApps/bridge-shim/python/main.py
  arduino-app-cli app restart user:bridge-shim
fi

podman-compose up --build --force-recreate -t 0 -d "$SERVICE"
