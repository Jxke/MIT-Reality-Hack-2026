#!/usr/bin/env python3
"""Test Arduino Uno Q <-> Debian comms through arduino-router.

Connects to the MsgPack-RPC Unix socket and listens for the two notification
types the sketch emits:

  [2, "direction", "front,150"]   — sound direction + peak volume
  [2, "audio",    [0, -3, 5, …]] — signed 8-bit PCM samples @ 8000 Hz

Usage:
  ./test-arduino.py [--socket PATH] [--timeout SECS]

Pass if both message types are received within the timeout.
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
    subprocess.check_call(["sudo", "apt-get", "install", "-y", "python3-msgpack"])
    import msgpack

SOCKET_PATH = "/var/run/arduino-router.sock"
DEFAULT_TIMEOUT = 10  # seconds to wait for both message types


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

    print(f"      Connected.")
    print(f"[2/3] Waiting up to {args.timeout}s for direction + audio messages ...")

    conn.settimeout(args.timeout)
    unpacker = msgpack.Unpacker(raw=False)

    seen = {"direction": False, "audio": False}
    counts = {"direction": 0, "audio": 0, "unknown": 0}
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
                    continue

                topic, payload = msg[1], msg[2]

                if topic == "direction":
                    counts["direction"] += 1
                    if not seen["direction"]:
                        seen["direction"] = True
                        try:
                            dir_str, vol_str = payload.split(",", 1)
                            print(f"      direction: {dir_str}  volume: {vol_str}")
                        except (ValueError, AttributeError):
                            print(f"      direction: (bad payload) {payload!r}")

                elif topic == "audio":
                    counts["audio"] += 1
                    if not seen["audio"]:
                        seen["audio"] = True
                        n = len(payload) if isinstance(payload, (list, bytes)) else "?"
                        print(f"      audio:     {n} samples/packet")

                else:
                    counts["unknown"] += 1

                if seen["direction"] and seen["audio"]:
                    break

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

    failures = []
    if not seen["direction"]:
        failures.append("no 'direction' notifications received")
    if not seen["audio"]:
        failures.append("no 'audio' notifications received")

    if failures:
        for f in failures:
            print(f"FAIL  {f}")
        sys.exit(1)

    print("PASS  Arduino <-> Debian communication working.")


if __name__ == "__main__":
    main()
