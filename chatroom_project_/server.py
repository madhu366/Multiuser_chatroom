import socket
import ssl
import threading
import pickle
import struct
import cv2

host = '0.0.0.0'
port = 12345
video_port = 12347

# SSL context setup
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')

# Wrap chat socket using SSL later after accept
raw_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
raw_server.bind((host, port))
raw_server.listen()

# Plain socket for video stream
video_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
video_server.bind((host, video_port))
video_server.listen()

clients = []
usernames = {}
credentials = {
    'user1': 'pass1',
    'user2': 'pass2',
    'user3': 'pass3',
    'user4': 'pass4',
    'madhu': 'madhu',
    'yashu': 'yashu'
}
viewers = []
sender_conn = None
sender_lock = threading.Lock()

def broadcast(message, _client=None):
    for client in clients:
        if client != _client:
            try:
                client.send(message.encode())
            except:
                remove_client(client)

def handle_client(client):
    try:
        client.send("Username: ".encode())
        username = client.recv(1024).decode().strip()
        client.send("Password: ".encode())
        password = client.recv(1024).decode().strip()

        if credentials.get(username) != password:
            client.send("Authentication failed.\n".encode())
            client.close()
            return

        usernames[client] = username
        clients.append(client)
        print(f"[+] {username} connected.")
        broadcast(f"{username} joined the chat.", client)
        client.send("You are connected! Type your messages below:\n".encode())

        while True:
            msg = client.recv(1024).decode().strip()
            if msg.startswith("/sendfile|"):
                parts = msg.split("|")
                filename = parts[1]
                filesize = int(parts[2])
                file_data = b''
                while len(file_data) < filesize:
                    chunk = client.recv(min(1024, filesize - len(file_data)))
                    if not chunk:
                        break
                    file_data += chunk
                with open(f"received_{filename}", "wb") as f:
                    f.write(file_data)
                broadcast(f"{usernames[client]} shared a file: {filename}", client)
            else:
                broadcast(f"{usernames[client]}: {msg}", client)
    except Exception as e:
        print(f"[ERROR] Client {usernames.get(client, 'Unknown')}: {e}")
    finally:
        remove_client(client)

def remove_client(client):
    if client in clients:
        print(f"[-] {usernames.get(client, 'Unknown')} disconnected.")
        broadcast(f"{usernames.get(client, 'A user')} left the chat.")
        clients.remove(client)
        client.close()
        if client in usernames:
            del usernames[client]

def video_server_thread():
    global sender_conn
    while True:
        try:
            conn, addr = video_server.accept()
            role = conn.recv(10).decode().strip()
            if role == "viewer":
                with sender_lock:
                    viewers.append(conn)
                print(f"[Viewer connected] Total viewers: {len(viewers)}")
            elif role == "sender":
                with sender_lock:
                    if sender_conn:
                        conn.send("Another sender is active.".encode())
                        conn.close()
                        continue
                    sender_conn = conn
                print("[Sender connected]")
                threading.Thread(target=stream_sender_to_viewers, args=(conn,), daemon=True).start()
        except Exception as e:
            print(f"[ERROR] Video server: {e}")

def stream_sender_to_viewers(conn):
    global sender_conn
    data = b''
    payload_size = struct.calcsize("Q")
    try:
        while True:
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet:
                    return
                data += packet
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data) < msg_size:
                packet = conn.recv(4096)
                if not packet:
                    return
                data += packet
            frame_data = data[:msg_size]
            data = data[msg_size:]

            with sender_lock:
                for viewer in viewers[:]:
                    try:
                        viewer.sendall(struct.pack("Q", len(frame_data)) + frame_data)
                    except:
                        viewers.remove(viewer)
                        print(f"[Viewer disconnected] Total viewers: {len(viewers)}")
    except Exception as e:
        print(f"[ERROR] Stream sender: {e}")
    finally:
        with sender_lock:
            if sender_conn == conn:
                sender_conn = None
            conn.close()
        print("[Sender disconnected]")

print(f"[SERVER STARTED WITH SSL] Listening on port {port}...")
threading.Thread(target=video_server_thread, daemon=True).start()

while True:
    try:
        raw_client, addr = raw_server.accept()
        client = context.wrap_socket(raw_client, server_side=True)
        threading.Thread(target=handle_client, args=(client,), daemon=True).start()
    except Exception as e:
        print(f"[ERROR] Main server: {e}")
