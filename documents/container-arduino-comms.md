# Container ↔ Arduino Communication: Problems & Solutions

## Context

During the container rewrite (`feature/container-rewrite`), the Python pipeline was moved out of the Arduino UNO Q Linux MPU and into a Podman container. This broke the existing Arduino communication approach.

---

## Problem 1: `arduino.app_utils` Not Available in Container

### Symptom
```
ModuleNotFoundError: No module named 'arduino'
```

### Root Cause
The old `Arduino/python/main.py` used `from arduino.app_utils import Bridge, App` and ran **directly on the Arduino Linux MPU** as a managed app under `arduino-app-cli`. The `arduino.app_utils` library communicates with `arduino-app-cli` on `127.0.0.1:8800` — a localhost-only daemon. It is not installed in the container and cannot be reached from outside the MPU.

### Solution
Replaced with `bridge_shim.py` (see Problem 3).

---

## Problem 2: `arduino-router` Unix Socket Does Not Stream Without Subscription

### Symptom
Connecting to `/var/run/arduino-router.sock` (mounted into the container via Podman volume) yielded no data. `socat` confirmed the connection was accepted but nothing was received.

### Investigation
- `/dev/ttyHS1` showed live MsgPack data from the MCU (`direction`, `audio` topics), confirming the sketch was running.
- `journalctl -u arduino-router` showed "Accepted connection" then "Connection closed by peer" — arduino-router held the connection open but sent nothing.
- Port 7500 (localhost) streams `Monitor.println()` output immediately on connect with no handshake — confirming arduino-router does serve data, just not on the unix socket without the right call.
- Sending MsgPack-RPC requests to the socket:
  - `[0, 1, "subscribe", [...]]` → `[1, 1, [2, "method subscribe not available"], None]`
  - `[0, 1, "provide",   [...]]` → `[1, 1, [2, "method provide not available"], None]`

### Root Cause
`arduino-router` is a Go MsgPack-RPC daemon that requires a specific subscription handshake before it streams notifications. The correct method name is undocumented. The `arduino.app_utils` Python library (which calls into `arduino-app-cli` on port 8800) is the **supported** interface — `arduino-router`'s socket API is an internal implementation detail not intended for direct use.

### Solution
Replaced with `bridge_shim.py` (see Problem 3).

---

## Problem 3: Solution — `bridge_shim.py`

**File:** `sound-sense/mcu/bridge_shim.py`

A small Python shim that runs on the Arduino Linux MPU (using the supported `arduino.app_utils` interface) and re-exposes Bridge notifications over TCP so the pipeline container can receive them.

```
Arduino MCU
  └─ Bridge.notify("direction" / "audio")
Arduino Linux MPU — bridge_shim.py
  ├─ Bridge.provide("direction", ...) via arduino.app_utils
  ├─ Bridge.provide("audio", ...)     via arduino.app_utils
  └─ TCP server :7000 → MsgPack-RPC [2, topic, payload]
Podman container — pipeline
  └─ ArduinoClient connects to 127.0.0.1:7000
     (works because network_mode: host)
```

MsgPack-RPC notification format (same as arduino-router emits internally):
```
[2, "direction", "front,150"]     — direction string + peak volume
[2, "audio",    [0, -3, 5, …]]   — signed 8-bit PCM samples @ 8000 Hz
```

Started by `scripts/restart-router.sh` alongside arduino-router.

---

## Port Reference

| Port | Owner | Protocol | Description |
|------|-------|----------|-------------|
| 7000 | bridge_shim.py | MsgPack-RPC TCP | Bridge.notify() forwarded to container |
| 7500 | arduino-router | Plain text TCP | Monitor.println() output (localhost only) |
| 8800 | arduino-app-cli | Internal | Manages Python apps using arduino.app_utils |
| 9001 | pipeline | TCP (S…E\n JSON) | AR/Unity caption + direction output |
