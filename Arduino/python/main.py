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
            threading.Thread(target=receive_tcp, args=(client_socket, address), daemon=True).start()
            # Send initial value
            try:
                message = ("S" + latest["value"] + "E" + "\n").encode()
                client_socket.sendall(message)
            except (socket.error, OSError):
                tcp_clients.remove(client_socket)
                client_socket.close()
        except Exception as e:
            print(f"TCP server error: {e}")

def receive_tcp(client_socket, address):
    buffer = ""
    try:
        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            chunk = data.decode(errors='replace')
            print(f"TCP recv raw from {address}: {chunk.strip()}")
            buffer += chunk

            while True:
                start = buffer.find("S")
                end = buffer.find("E", start + 1)
                if start == -1 or end == -1:
                    break
                payload = buffer[start + 1:end]
                print(f"TCP recv framed from {address}: {payload}")
                latest["value"] = payload
                message = ("S" + payload + "E" + "\n").encode()
                disconnected_clients = []
                for other_client in tcp_clients:
                    if other_client is client_socket:
                        continue
                    try:
                        other_client.sendall(message)
                    except (socket.error, OSError):
                        disconnected_clients.append(other_client)
                for other in disconnected_clients:
                    tcp_clients.remove(other)
                    try:
                        other.close()
                    except Exception:
                        pass
                buffer = buffer[end + 1:]
    except Exception as e:
        print(f"TCP recv error from {address}: {e}")
    finally:
        try:
            tcp_clients.remove(client_socket)
        except ValueError:
            pass
        try:
            client_socket.close()
        except Exception:
            pass
        print(f"TCP client disconnected: {address}")

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
