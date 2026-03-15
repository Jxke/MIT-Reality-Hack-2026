#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKETCH_DIR="$SCRIPT_DIR/../mcu/sketch"

FQBN="arduino:zephyr:unoq"
PORT=""

usage() {
  echo "Usage: deploy-mcu.sh [--port <device>] [--fqbn <fqbn>]"
  echo ""
  echo "Compile and upload the sketch to the Arduino UNO R4 (Zephyr/RouterBridge)."
  echo ""
  echo "Options:"
  echo "  --port <device>   Serial port (e.g. /dev/ttyACM0). Auto-detected if omitted."
  echo "  --fqbn <fqbn>     Board FQBN (default: $FQBN)"
  echo "  -h, --help        Show this help message"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage ;;
    --port)    PORT="$2"; shift 2 ;;
    --fqbn)    FQBN="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

if ! command -v arduino-cli &>/dev/null; then
  echo "Error: arduino-cli not found. Install it from https://arduino.github.io/arduino-cli/"
  exit 1
fi

# Auto-detect port if not specified
if [[ -z "$PORT" ]]; then
  PORT=$(arduino-cli board list 2>/dev/null | awk '{print $1}' | grep -E '^/dev/tty' | head -1)
  if [[ -z "$PORT" ]]; then
    echo "Error: no Arduino detected. Connect the board or use --port /dev/ttyACM0"
    exit 1
  fi
  echo "Detected port: $PORT"
fi

echo "=== Installing core (arduino:zephyr) if needed ==="
arduino-cli core update-index
arduino-cli core install arduino:zephyr

echo ""
echo "=== Installing libraries if needed ==="
arduino-cli lib install "Arduino_RouterBridge" 2>/dev/null || true

echo ""
echo "=== Compiling sketch ==="
arduino-cli compile --fqbn "$FQBN" "$SKETCH_DIR"

echo ""
echo "=== Uploading to $PORT ==="
arduino-cli upload --fqbn "$FQBN" --port "$PORT" "$SKETCH_DIR"

echo ""
echo "Done. Sketch deployed to $PORT"
