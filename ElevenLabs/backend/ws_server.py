"""
WebSocket server for broadcasting caption events to Unity clients
"""

import asyncio
import websockets
import json
import logging
from typing import Set
from config import WS_HOST, WS_PORT

logger = logging.getLogger(__name__)


class WebSocketServer:
    """WebSocket server that broadcasts caption events to all connected clients"""
    
    def __init__(self, host: str = WS_HOST, port: int = WS_PORT):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.server = None
        
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client connection"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
    async def broadcast(self, message: dict):
        """
        Broadcast message to all connected clients
        
        Args:
            message: Dictionary to send (will be JSON serialized)
        """
        if not self.clients:
            return
        
        message_json = json.dumps(message)
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(message_json)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    async def start(self):
        """Start WebSocket server"""
        async def handler(websocket: websockets.WebSocketServerProtocol, path: str):
            await self.register_client(websocket)
        
        self.server = await websockets.serve(handler, self.host, self.port)
        logger.info(f"WebSocket server started on ws://{self.host}:{self.port}")
    
    async def stop(self):
        """Stop WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("WebSocket server stopped")
