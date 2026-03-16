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
Replaced with `bridge_shim.py` (see Solution section below).

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

---

## Solution — `bridge_shim.py` as an Arduino App

**Repo file:** `sound-sense/mcu/bridge_shim.py`
**Deployed to:** `/home/arduino/ArduinoApps/bridge-shim/python/main.py`
**Managed by:** `arduino-app-cli` as app `user:bridge-shim`

A small Python shim that runs on the Arduino Linux MPU (using the supported `arduino.app_utils` interface) and re-exposes Bridge notifications over TCP so the pipeline container can receive them.

```
Arduino MCU
  └─ Bridge.notify("direction" / "audio")
Arduino Linux MPU — bridge_shim.py  (arduino-app-cli: user:bridge-shim)
  ├─ Bridge.provide("direction", ...) via arduino.app_utils
  ├─ Bridge.provide("audio", ...)     via arduino.app_utils
  └─ TCP server :7000 → MsgPack-RPC [2, topic, payload]
Podman container — pipeline
  └─ ArduinoClient connects to 127.0.0.1:7000
     (works because network_mode: host)
```

MsgPack-RPC notification format:
```
[2, "direction", "front,150"]     — direction string + peak volume
[2, "audio",    [0, -3, 5, …]]   — signed 8-bit PCM samples @ 8000 Hz
```

### First-time Setup

The Arduino app only needs to be created once:

```bash
arduino-app-cli app new bridge-shim --description "Bridge shim: forwards Bridge.notify to TCP" --no-sketch
# Edit /home/arduino/ArduinoApps/bridge-shim/app.yaml and set: ports: [7000]
cp sound-sense/mcu/bridge_shim.py /home/arduino/ArduinoApps/bridge-shim/python/main.py
arduino-app-cli app start user:bridge-shim
```

### Day-to-day Operation

All scripts in `sound-sense/scripts/` handle the bridge shim automatically:

| Script | Bridge shim action |
|--------|--------------------|
| `start.sh` | Syncs `bridge_shim.py` → app, restarts app, then starts containers |
| `stop.sh` | Stops containers, then stops app |
| `status.sh` | Shows app status alongside container status |
| `logs.sh` | Shows last 20 app log lines, then follows container logs |
| `restart-router.sh` | Syncs + restarts app after arduino-router restart |

To check bridge shim logs directly:
```bash
arduino-app-cli app logs user:bridge-shim
```

---

## Port Reference

| Port | Owner | Protocol | Description |
|------|-------|----------|-------------|
| 7000 | bridge_shim (user:bridge-shim) | MsgPack-RPC TCP | Bridge.notify() forwarded to container |
| 7500 | arduino-router | Plain text TCP | Monitor.println() output (localhost only) |
| 8800 | arduino-app-cli | Internal HTTP | Manages Python apps via arduino.app_utils |
| 9001 | pipeline container | TCP (`S…E\n` JSON) | AR/Unity caption + direction output |
