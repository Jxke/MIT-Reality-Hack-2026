#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: start.sh [--rebuild]"
  echo ""
  echo "Start all containers in detached mode."
  echo ""
  echo "Options:"
  echo "  --rebuild   Rebuild images before starting"
  echo "  -h, --help  Show this help message"
  exit 0
fi

BUILD_FLAG=""
if [[ "${1:-}" == "--rebuild" ]]; then
  BUILD_FLAG="--build"
fi

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

echo "=== Syncing and starting bridge shim ==="
cp "$SCRIPT_DIR/../mcu/bridge_shim.py" /home/arduino/ArduinoApps/bridge-shim/python/main.py
arduino-app-cli app restart user:bridge-shim

echo "=== Starting containers ==="
podman-compose up --force-recreate -t 0 $BUILD_FLAG -d
