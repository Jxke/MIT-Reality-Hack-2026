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

# Load env for ARDUINO_PORT
set -a; source .env; set +a

# Start arduino-router (connects to MCU over USB, exposes MsgPack-RPC on ARDUINO_PORT)
SERIAL_PORT=$(ls /dev/ttyACM* /dev/ttyUSB* 2>/dev/null | head -1)
if [[ -z "$SERIAL_PORT" ]]; then
  echo "Warning: no Arduino serial port found, skipping arduino-router"
else
  echo "Starting arduino-router on $SERIAL_PORT -> localhost:${ARDUINO_PORT}"
  arduino-router \
    --serial-port "$SERIAL_PORT" \
    --listen-port "127.0.0.1:${ARDUINO_PORT}" \
    > /tmp/arduino-router.log 2>&1 &
  echo $! > /tmp/arduino-router.pid
fi

podman-compose up $BUILD_FLAG -d
