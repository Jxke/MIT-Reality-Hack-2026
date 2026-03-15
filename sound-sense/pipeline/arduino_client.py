import json
import logging
import socket
import threading
import time


class ArduinoClient:
    """TCP client that connects to the Arduino Uno acting as TCP server.
    Runs in a background thread, auto-reconnects on disconnect."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._latest: dict = {}
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def get_latest(self) -> dict:
        with self._lock:
            return dict(self._latest)

    def _run(self):
        while True:
            try:
                with socket.create_connection((self.host, self.port), timeout=5) as sock:
                    logging.info(f"Connected to Arduino at {self.host}:{self.port}")
                    buf = ""
                    while True:
                        data = sock.recv(1024).decode()
                        if not data:
                            break
                        buf += data
                        while "\n" in buf:
                            line, buf = buf.split("\n", 1)
                            try:
                                parsed = json.loads(line)
                                with self._lock:
                                    self._latest = parsed
                            except json.JSONDecodeError:
                                logging.warning(f"Invalid JSON from Arduino: {line!r}")
            except (socket.error, OSError) as e:
                logging.warning(f"Arduino connection error: {e}, retrying in 5s")
                time.sleep(5)
