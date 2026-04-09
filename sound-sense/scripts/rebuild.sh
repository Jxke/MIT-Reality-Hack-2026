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

if [[ "$SERVICE" == "pipeline" ]]; then
  echo "=== Syncing and restarting bridge shim ==="
  cp "$SCRIPT_DIR/../mcu/bridge_shim.py" /home/arduino/ArduinoApps/bridge-shim/python/main.py
  arduino-app-cli app restart user:bridge-shim
fi

podman-compose up --build --force-recreate -t 0 -d "$SERVICE"
