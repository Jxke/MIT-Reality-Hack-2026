import logging
import socket
import threading

import msgpack


class ArduinoServer:
    """TCP server the Arduino RouterBridge connects to.

    Expects MsgPack-framed messages of the form [topic, payload] matching
    the sketch's Bridge.notify() calls:

      ["direction", "front,150"]   — direction + peak volume string
      ["audio",     [0, -3, 5, …]] — signed 8-bit PCM samples
    """

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
            logging.warning(f"Arduino connection error: {e}")
        finally:
            conn.close()
            logging.info(f"Arduino disconnected from {addr}")

    def _process(self, msg):
        if not isinstance(msg, (list, tuple)) or len(msg) < 2:
            logging.warning(f"Unexpected message format: {msg!r}")
            return

        topic, payload = msg[0], msg[1]

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
