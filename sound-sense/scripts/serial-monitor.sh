#!/usr/bin/env bash
set -euo pipefail

PORT=""
BAUD="9600"

usage() {
  echo "Usage: serial-monitor.sh [--port <device>] [--baud <rate>]"
  echo ""
  echo "Watch the Arduino serial monitor (MCU debug output via Monitor.println)."
  echo ""
  echo "Options:"
  echo "  --port <device>   Serial port (e.g. /dev/ttyACM0). Auto-detected if omitted."
  echo "  --baud <rate>     Baud rate (default: $BAUD)"
  echo "  -h, --help        Show this help message"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage ;;
    --port)    PORT="$2"; shift 2 ;;
    --baud)    BAUD="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

if ! command -v arduino-cli &>/dev/null; then
  echo "Error: arduino-cli not found. Install it from https://arduino.github.io/arduino-cli/"
  exit 1
fi

if [[ -z "$PORT" ]]; then
  PORT=$(arduino-cli board list 2>/dev/null | grep -i "arduino\|ttyACM\|ttyUSB" | awk '{print $1}' | head -1)
  if [[ -z "$PORT" ]]; then
    echo "Error: no Arduino detected. Connect the board or use --port /dev/ttyACM0"
    exit 1
  fi
  echo "Detected port: $PORT"
fi

echo "=== Serial monitor on $PORT @ ${BAUD} baud (Ctrl+C to quit) ==="
arduino-cli monitor --port "$PORT" --config "baudrate=$BAUD"
