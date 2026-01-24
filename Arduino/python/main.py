# main.py (runs on the UNO Q Linux/MPU side)
from arduino.app_utils import Bridge, App
import threading
import socket

latest = {"value": "no data yet"}
tcp_clients = []  # List of connected TCP clients

def mcu_line(msg: str):
    latest["value"] = msg
    # Broadcast to all connected TCP clients
    message = ("S" + latest["value"] + "E" + "\n").encode()
    disconnected_clients = []
    for client_socket in tcp_clients:
        try:
            client_socket.sendall(message)
        except (socket.error, OSError):
            disconnected_clients.append(client_socket)
    # Remove disconnected clients
    for client in disconnected_clients:
        tcp_clients.remove(client)
        try:
            client.close()
        except:
            pass

Bridge.provide("mcu_line", mcu_line)

def serve_tcp():
    # TCP server for persistent connections (Unity, etc.)
    tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tcp_server.bind(("0.0.0.0", 7000))
    tcp_server.listen(5)
    print("TCP server listening on port 7000")
    
    while True:
        try:
            client_socket, address = tcp_server.accept()
            print(f"TCP client connected: {address}")
            tcp_clients.append(client_socket)
            # Send initial value
            try:
                message = ("S" + latest["value"] + "E" + "\n").encode()
                client_socket.sendall(message)
            except (socket.error, OSError):
                tcp_clients.remove(client_socket)
                client_socket.close()
        except Exception as e:
            print(f"TCP server error: {e}")

def get_ip():
    # Works well when you're connected to Wi-Fi / hotspot and have a default route.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 7000))   # no packets need to actually be sent
        return s.getsockname()[0]
    finally:
        s.close()


print("IP Address:", get_ip())

threading.Thread(target=serve_tcp, daemon=True).start()
App.run()