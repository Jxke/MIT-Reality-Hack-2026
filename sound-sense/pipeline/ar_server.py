import json
import logging
import socket
import threading


class ARServer:
    """TCP server that AR devices connect to. Broadcasts JSON messages to all connected clients."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._clients: list[socket.socket] = []
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def broadcast(self, message: dict):
        data = ("S" + json.dumps(message) + "E\n").encode()
        with self._lock:
            dead = []
            for client in self._clients:
                try:
                    client.sendall(data)
                except OSError:
                    dead.append(client)
            for c in dead:
                self._clients.remove(c)
                c.close()

    def _run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()
            logging.info(f"AR server listening on {self.host}:{self.port}")
            while True:
                try:
                    client, addr = server.accept()
                    logging.info(f"AR device connected from {addr}")
                    with self._lock:
                        self._clients.append(client)
                except OSError as e:
                    logging.error(f"AR server accept error: {e}")
