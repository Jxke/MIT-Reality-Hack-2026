#!/usr/bin/env bash
# Restart arduino-router, draining the UART first so the 0x00 MCU boot
# byte doesn't kill the router's serial goroutine.
set -euo pipefail

echo "=== Stopping arduino-router ==="
sudo systemctl stop arduino-router

echo "=== Draining UART boot bytes (5s) ==="
sudo timeout 5 dd if=/dev/ttyHS1 of=/dev/null bs=1 2>/dev/null || true

echo "=== Starting arduino-router ==="
sudo systemctl start arduino-router

echo "=== Restarting bridge shim ==="
cp "$(dirname "$0")/../mcu/bridge_shim.py" /home/arduino/ArduinoApps/bridge-shim/python/main.py
arduino-app-cli app restart user:bridge-shim

echo "=== Restarting pipeline container ==="
cd "$(dirname "$0")/.." && podman-compose restart pipeline
