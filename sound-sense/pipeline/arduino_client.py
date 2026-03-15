import logging
import socket
import threading
import time

import msgpack


class ArduinoClient:
    """Client that connects to arduino-router's Unix socket MsgPack-RPC service.

    arduino-router listens on ARDUINO_SOCKET and streams MsgPack-RPC
    notifications from the sketch's Bridge.notify() calls:

      [2, "direction", "front,150"]   — direction + peak volume
      [2, "audio",    [0, -3, 5, …]] — signed 8-bit PCM samples
    """

    RECONNECT_DELAY = 3  # seconds between reconnect attempts

    def __init__(self, socket_path: str, on_message=None):
        self.socket_path = socket_path
        self._latest: dict = {}
        self._lock = threading.Lock()
        self._on_message = on_message
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def get_latest(self) -> dict:
        with self._lock:
            return dict(self._latest)

    SUBSCRIBE_TOPICS = ["direction", "audio"]

    def _connect(self) -> socket.socket:
        while True:
            try:
                conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                conn.connect(self.socket_path)
                # MsgPack-RPC request: [0, msgid, "subscribe", [topics...]]
                conn.sendall(msgpack.packb([0, 1, "subscribe", self.SUBSCRIBE_TOPICS]))
                logging.info(f"Connected to arduino-router at {self.socket_path}, subscribed to {self.SUBSCRIBE_TOPICS}")
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
        print(f"[arduino-raw] {msg!r}", flush=True)
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
                if self._on_message:
                    self._on_message("direction", {"direction": dir_str, "volume": int(vol_str)})
            except (ValueError, AttributeError) as e:
                logging.warning(f"Bad direction payload {payload!r}: {e}")

        elif topic == "audio":
            # payload: list of int8 PCM samples
            with self._lock:
                self._latest["audio"] = payload
            logging.debug(f"Audio packet: {len(payload)} samples")
            if self._on_message:
                self._on_message("audio", {"samples": len(payload)})

        else:
            logging.debug(f"Unknown topic: {topic!r}")
            if self._on_message:
                self._on_message(topic, payload)

    def _run(self):
        while True:
            conn = self._connect()
            self._handle(conn)
            logging.info(f"Reconnecting to arduino-router in {self.RECONNECT_DELAY}s")
            time.sleep(self.RECONNECT_DELAY)
