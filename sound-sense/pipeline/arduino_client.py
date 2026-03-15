import json
import logging
import socket
import threading


class ArduinoServer:
    """TCP server the Arduino connects to. Accepts one client at a time and
    tracks the latest JSON message received from it."""

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

    def _handle(self, conn: socket.socket, addr):
        logging.info(f"Arduino connected from {addr}")
        buf = ""
        try:
            while True:
                data = conn.recv(1024).decode()
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
        except OSError as e:
            logging.warning(f"Arduino connection error: {e}")
        finally:
            conn.close()
            logging.info(f"Arduino disconnected from {addr}")

    def _run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()
            logging.info(f"Arduino server listening on {self.host}:{self.port}")
            while True:
                try:
                    conn, addr = server.accept()
                    threading.Thread(target=self._handle, args=(conn, addr), daemon=True).start()
                except OSError as e:
                    logging.error(f"Arduino server accept error: {e}")
