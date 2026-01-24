#!/usr/bin/env python3
"""
Simple WebSocket client to test caption events from backend
Run this while backend is running to see caption events
"""

import asyncio
import json
import websockets


async def test_websocket():
    """Connect to WebSocket server and print received messages"""
    uri = "ws://localhost:8765"
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            print("Waiting for caption events... (speak into microphone or generate sounds)\n")
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("type") == "caption":
                        print(f"[{data.get('mode', 'unknown').upper()}] {data.get('text', '')}")
                        print(f"  Direction: {data.get('direction', 0)}, "
                              f"Confidence: {data.get('confidence', 0.0):.2f}, "
                              f"Final: {data.get('isFinal', False)}")
                        print()
                except json.JSONDecodeError:
                    print(f"Received non-JSON: {message}")
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {uri}")
        print("Make sure the backend is running: python backend/main.py")
    except KeyboardInterrupt:
        print("\nDisconnected")


if __name__ == "__main__":
    asyncio.run(test_websocket())
