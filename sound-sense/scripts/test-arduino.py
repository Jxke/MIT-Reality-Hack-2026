#!/usr/bin/env python3
"""Test Arduino Uno Q <-> Debian comms through arduino-router.

Connects to the MsgPack-RPC Unix socket and listens for the two notification
types the sketch emits:

  [2, "direction", "front,150"]   — sound direction + peak volume
  [2, "audio",    [0, -3, 5, …]] — signed 8-bit PCM samples @ 8000 Hz

Usage:
  ./test-arduino.py [--socket PATH] [--timeout SECS]

Pass if both message types are received within the timeout and payloads are valid.
"""

import argparse
import socket
import sys
import time

try:
    import msgpack
except ImportError:
    import subprocess
    print("msgpack not found, installing...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "msgpack"])
    import msgpack

SOCKET_PATH = "/var/run/arduino-router.sock"
DEFAULT_TIMEOUT = 10  # seconds to wait for both message types

VALID_DIRECTIONS = {"front", "back", "left", "right", "none"}
VOLUME_MAX = 2048    # 12-bit ADC range
AUDIO_PACKET_SIZE = 128  # samples per packet (~16ms @ 8000 Hz)
SAMPLE_MIN, SAMPLE_MAX = -128, 127  # signed 8-bit PCM


def validate_direction(payload) -> list[str]:
    errors = []
    if not isinstance(payload, str):
        return [f"expected str, got {type(payload).__name__}"]
    parts = payload.split(",", 1)
    if len(parts) != 2:
        return [f"expected 'direction,volume', got {payload!r}"]
    dir_str, vol_str = parts
    if dir_str not in VALID_DIRECTIONS:
        errors.append(f"unknown direction {dir_str!r} (expected one of {sorted(VALID_DIRECTIONS)})")
    try:
        vol = int(vol_str)
        if not (0 <= vol <= VOLUME_MAX):
            errors.append(f"volume {vol} out of range [0, {VOLUME_MAX}]")
    except ValueError:
        errors.append(f"non-integer volume {vol_str!r}")
    return errors


def validate_audio(payload) -> list[str]:
    errors = []
    if not isinstance(payload, (list, bytes)):
        return [f"expected list or bytes, got {type(payload).__name__}"]
    n = len(payload)
    if n == 0:
        errors.append("empty audio packet")
    elif n != AUDIO_PACKET_SIZE:
        errors.append(f"unexpected packet size {n} (expected {AUDIO_PACKET_SIZE})")
    if isinstance(payload, list):
        oob = [s for s in payload if not (SAMPLE_MIN <= s <= SAMPLE_MAX)]
        if oob:
            errors.append(f"{len(oob)} sample(s) out of signed 8-bit range")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--socket", default=SOCKET_PATH, help=f"Unix socket path (default: {SOCKET_PATH})")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help=f"Seconds to wait (default: {DEFAULT_TIMEOUT})")
    args = parser.parse_args()

    print(f"[1/3] Connecting to arduino-router at {args.socket} ...")
    try:
        conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        conn.connect(args.socket)
    except FileNotFoundError:
        print(f"FAIL  Socket not found: {args.socket}")
        print("      Is arduino-router running? Check: systemctl is-active arduino-router")
        sys.exit(1)
    except OSError as e:
        print(f"FAIL  Cannot connect: {e}")
        sys.exit(1)

    for i, topic in enumerate(["direction", "audio"]):
        conn.sendall(msgpack.packb([0, i, "provide", [topic]]))
    print(f"      Connected, sent provide requests.")
    print(f"[2/3] Waiting up to {args.timeout}s for direction + audio messages ...")

    unpacker = msgpack.Unpacker(raw=False)
    seen = {"direction": False, "audio": False}
    counts = {"direction": 0, "audio": 0, "unknown": 0}
    warnings: list[str] = []
    deadline = time.monotonic() + args.timeout

    try:
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            conn.settimeout(max(remaining, 0.1))
            try:
                data = conn.recv(4096)
            except TimeoutError:
                break
            if not data:
                print("FAIL  Connection closed by arduino-router.")
                sys.exit(1)

            unpacker.feed(data)
            for msg in unpacker:
                if not isinstance(msg, (list, tuple)) or len(msg) < 3 or msg[0] != 2:
                    counts["unknown"] += 1
                    print(f"      unknown: {msg!r}")
                    continue

                topic, payload = msg[1], msg[2]

                if topic == "direction":
                    counts["direction"] += 1
                    errs = validate_direction(payload)
                    if errs:
                        warnings.extend(f"direction payload: {e}" for e in errs)
                    if not seen["direction"]:
                        seen["direction"] = True
                        try:
                            dir_str, vol_str = payload.split(",", 1)
                            print(f"      direction: {dir_str}  volume: {vol_str}")
                        except (ValueError, AttributeError):
                            print(f"      direction: (bad payload) {payload!r}")

                elif topic == "audio":
                    counts["audio"] += 1
                    errs = validate_audio(payload)
                    if errs:
                        warnings.extend(f"audio payload: {e}" for e in errs)
                    if not seen["audio"]:
                        seen["audio"] = True
                        n = len(payload) if isinstance(payload, (list, bytes)) else "?"
                        print(f"      audio:     {n} samples/packet")

                else:
                    counts["unknown"] += 1

            if seen["direction"] and seen["audio"]:
                break

    except OSError as e:
        print(f"FAIL  Socket error: {e}")
        sys.exit(1)
    finally:
        conn.close()

    print(f"[3/3] Results:")
    print(f"      direction packets : {counts['direction']}")
    print(f"      audio packets     : {counts['audio']}")
    if counts["unknown"]:
        print(f"      unknown messages  : {counts['unknown']}")

    for w in warnings:
        print(f"WARN  {w}")

    failures = []
    if not seen["direction"]:
        failures.append("no 'direction' notifications received")
    if not seen["audio"]:
        failures.append("no 'audio' notifications received")
    if warnings:
        failures.extend(warnings)

    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        sys.exit(1)

    print("PASS  Arduino <-> Debian communication working.")


if __name__ == "__main__":
    main()
