#!/usr/bin/env python3
"""
Simple TCP client to test caption events from backend
Run this while backend is running to see caption events
"""

import socket


def test_tcp():
    """Connect to TCP server and print received messages"""
    host = "localhost"
    port = 7000

    try:
        with socket.create_connection((host, port)) as sock:
            print(f"Connected to {host}:{port}")
            print("Waiting for caption events... (speak into microphone or generate sounds)\n")

            while True:
                data = sock.recv(4096)
                if not data:
                    break
                print(data.decode("utf-8").strip())
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {host}:{port}")
        print("Make sure the backend is running: python backend/main.py")
    except KeyboardInterrupt:
        print("\nDisconnected")


if __name__ == "__main__":
    test_tcp()
