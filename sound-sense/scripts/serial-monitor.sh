#!/usr/bin/env bash
set -euo pipefail

MONITOR_HOST="127.0.0.1"
MONITOR_PORT="7500"

usage() {
  echo "Usage: serial-monitor.sh [--port <port>]"
  echo ""
  echo "Watch MCU debug output (Monitor.println) via the arduino-router monitor API."
  echo ""
  echo "Options:"
  echo "  --port <port>  Monitor API port (default: $MONITOR_PORT)"
  echo "  -h, --help     Show this help message"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)  usage ;;
    --port)     MONITOR_PORT="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

if ! systemctl is-active --quiet arduino-router; then
  echo "Error: arduino-router is not running."
  echo "Tip: sudo systemctl start arduino-router"
  exit 1
fi

if ! command -v nc &>/dev/null; then
  echo "Error: nc (netcat) not found."
  exit 1
fi

echo "=== MCU serial monitor on ${MONITOR_HOST}:${MONITOR_PORT} (Ctrl+C to quit) ==="
nc "$MONITOR_HOST" "$MONITOR_PORT"
