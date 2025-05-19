
import socket
import cv2
import pickle
import struct
import threading

HOST = '0.0.0.0'
PORT = 12346

clients = []

def handle_client(conn):
    try:
        role_data = conn.recv(10)
        if not role_data:
            return
        role = role_data.decode().strip()
        if role == "sender":
            print("[*] Sender connected")
            while True:
                packed_msg_size = conn.recv(8)
                if not packed_msg_size:
                    break
                msg_size = struct.unpack("Q", packed_msg_size)[0]
                data = b""
                while len(data) < msg_size:
                    packet = conn.recv(4096)
                    if not packet:
                        break
                    data += packet
                for c in clients:
                    try:
                        c.sendall(struct.pack("Q", len(data)) + data)
                    except:
                        pass
        else:
            print("[*] Viewer connected")
            clients.append(conn)
    except:
        pass
    finally:
        if conn in clients:
            clients.remove(conn)
        conn.close()

print(f"[STREAM SERVER STARTED] Listening on {HOST}:{PORT}")
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(5)

while True:
    client_socket, addr = server_socket.accept()
    threading.Thread(target=handle_client, args=(client_socket,)).start()
