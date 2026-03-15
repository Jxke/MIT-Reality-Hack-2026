import logging
import socket
import threading
import time

import msgpack


class ArduinoClient:
    """Client that connects to arduino-router's MsgPack-RPC service.

    arduino-router listens on ARDUINO_HOST:ARDUINO_PORT and streams
    MsgPack-RPC notifications from the sketch's Bridge.notify() calls:

      [2, "direction", "front,150"]   — direction + peak volume
      [2, "audio",    [0, -3, 5, …]] — signed 8-bit PCM samples
    """

    RECONNECT_DELAY = 3  # seconds between reconnect attempts

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

    def _connect(self) -> socket.socket:
        while True:
            try:
                conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                conn.connect((self.host, self.port))
                logging.info(f"Connected to arduino-router at {self.host}:{self.port}")
                return conn
            except OSError as e:
                logging.warning(f"arduino-router not available ({e}), retrying in {self.RECONNECT_DELAY}s")
                time.sleep(self.RECONNECT_DELAY)

    def _handle(self, conn: socket.socket):
        unpacker = msgpack.Unpacker(raw=False)
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                unpacker.feed(data)
                for msg in unpacker:
                    self._process(msg)
        except OSError as e:
            logging.warning(f"arduino-router connection lost: {e}")
        finally:
            conn.close()

    def _process(self, msg):
        # MsgPack-RPC notification: [2, method, params]
        if not isinstance(msg, (list, tuple)) or len(msg) < 3 or msg[0] != 2:
            logging.debug(f"Ignoring non-notification message: {msg!r}")
            return

        topic, payload = msg[1], msg[2]

        if topic == "direction":
            # payload: "front,150"
            try:
                dir_str, vol_str = payload.split(",", 1)
                with self._lock:
                    self._latest["direction"] = dir_str
                    self._latest["volume"] = int(vol_str)
                logging.info(f"Direction: {dir_str}, volume: {vol_str}")
            except (ValueError, AttributeError) as e:
                logging.warning(f"Bad direction payload {payload!r}: {e}")

        elif topic == "audio":
            # payload: list of int8 PCM samples
            with self._lock:
                self._latest["audio"] = payload
            logging.debug(f"Audio packet: {len(payload)} samples")

        else:
            logging.debug(f"Unknown topic: {topic!r}")

    def _run(self):
        while True:
            conn = self._connect()
            self._handle(conn)
            logging.info(f"Reconnecting to arduino-router in {self.RECONNECT_DELAY}s")
            time.sleep(self.RECONNECT_DELAY)
