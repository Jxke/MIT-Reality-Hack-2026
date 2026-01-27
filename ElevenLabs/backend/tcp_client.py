"""
TCP client for sending caption events to an existing TCP server
"""

import asyncio
import json
import logging
from config import TCP_HOST, TCP_PORT, TCP_MESSAGE_FORMAT, TCP_FRAME_PREFIX, TCP_FRAME_SUFFIX

logger = logging.getLogger(__name__)


class TCPClient:
    """TCP client that connects and sends caption events to a server"""

    def __init__(self, host: str = TCP_HOST, port: int = TCP_PORT):
        self.host = host
        self.port = port
        self._writer: asyncio.StreamWriter | None = None
        self._reader: asyncio.StreamReader | None = None
        self._lock = asyncio.Lock()
        self._running = False
        self._task: asyncio.Task | None = None

    def _encode_message(self, message: dict) -> bytes:
        if TCP_MESSAGE_FORMAT == "json":
            body = json.dumps(message, ensure_ascii=True)
        else:
            body = str(message.get("text", ""))
        framed = f"{TCP_FRAME_PREFIX}{body}{TCP_FRAME_SUFFIX}"
        return framed.encode("utf-8")

    async def _connect_loop(self):
        while self._running:
            try:
                logger.debug(f"Connecting to TCP server at {self.host}:{self.port}...")
                reader, writer = await asyncio.open_connection(self.host, self.port)
                async with self._lock:
                    self._reader = reader
                    self._writer = writer
                logger.debug("TCP client connected")

                while self._running:
                    data = await reader.read(1024)
                    if not data:
                        break
                    logger.debug(f"TCP server sent: {data.decode('utf-8', errors='replace').strip()}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"TCP client connection error: {e}")
            finally:
                async with self._lock:
                    if self._writer:
                        self._writer.close()
                        try:
                            await self._writer.wait_closed()
                        except Exception:
                            pass
                    self._reader = None
                    self._writer = None

                if self._running:
                    await asyncio.sleep(1.0)

    async def start(self):
        """Start TCP client connection loop"""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._connect_loop())

    async def stop(self):
        """Stop TCP client"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            self._task = None

        async with self._lock:
            if self._writer:
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception:
                    pass
            self._reader = None
            self._writer = None

    async def broadcast(self, message: dict):
        """Send message to TCP server (same interface as server broadcast)"""
        async with self._lock:
            writer = self._writer

        if not writer:
            logger.warning("TCP client not connected; caption not sent")
            return

        payload = self._encode_message(message)
        try:
            logger.info(f"Sending caption to TCP server: {payload.decode('utf-8', errors='replace').strip()}")
            writer.write(payload)
            await writer.drain()
        except (ConnectionError, OSError) as e:
            logger.warning(f"TCP send failed: {e}")
