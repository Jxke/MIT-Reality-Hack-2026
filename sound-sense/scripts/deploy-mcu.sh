#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKETCH_DIR="$SCRIPT_DIR/../mcu/sketch"

FQBN="arduino:zephyr:unoq"

echo "Script directory is $SCRIPT_DIR, sketch directory is $SKETCH_DIR";

usage() {
  echo "Usage: deploy-mcu.sh"
  echo ""
  echo "Compile and flash the sketch to the Arduino UNO Q (Zephyr/RouterBridge)."
  echo ""
  echo "Options:"
  echo "  -h, --help           Show this help message"
  exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)       usage ;;
    *) echo "Unknown argument: $1"; usage ;;
  esac
done

echo ""
echo "=== Compile and Upload to Arduino UNO Q ==="
arduino-cli compile --fqbn "$FQBN" ./
arduino-cli upload --fqbn "$FQBN"

echo ""
echo "=== Restarting arduino-router (with UART drain) ==="
"$SCRIPT_DIR/restart-router.sh"

echo ""
echo "Done. Sketch deployed and arduino-router restarted."
