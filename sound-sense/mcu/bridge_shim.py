#!/usr/bin/env python3
"""Bridge shim — forwards Arduino Bridge.notify() events to TCP clients.

Runs on the Arduino UNO Q Linux MPU (via arduino.app_utils).
Pipeline container connects on BRIDGE_PORT and receives MsgPack-RPC
notifications mirroring what the sketch emits:

  [2, "direction", "front,150"]   — sound direction + peak volume
  [2, "audio",    [0, -3, 5, …]] — signed 8-bit PCM samples @ 8000 Hz
"""

import os
import socket
import threading

import msgpack
from arduino.app_utils import App, Bridge

BRIDGE_HOST = os.environ.get("BRIDGE_HOST", "0.0.0.0")
BRIDGE_PORT = int(os.environ.get("BRIDGE_PORT", "7000"))

_clients = []
_lock = threading.Lock()


def _broadcast(topic: str, payload):
    msg = msgpack.packb([2, topic, payload])
    with _lock:
        dead = []
        for client in _clients:
            try:
                client.sendall(msg)
            except OSError:
                dead.append(client)
        for c in dead:
            _clients.remove(c)
            try:
                c.close()
            except Exception:
                pass


def _on_direction(msg: str):
    print(f"[bridge] direction: {msg}", flush=True)
    _broadcast("direction", msg)


def _on_audio(samples):
    _broadcast("audio", samples)


Bridge.provide("direction", _on_direction)
Bridge.provide("audio", _on_audio)


def _serve():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((BRIDGE_HOST, BRIDGE_PORT))
    server.listen(5)
    print(f"[bridge] listening on {BRIDGE_HOST}:{BRIDGE_PORT}", flush=True)
    while True:
        try:
            client, addr = server.accept()
            print(f"[bridge] client connected: {addr}", flush=True)
            with _lock:
                _clients.append(client)
        except Exception as e:
            print(f"[bridge] accept error: {e}", flush=True)


threading.Thread(target=_serve, daemon=True).start()
App.run()
