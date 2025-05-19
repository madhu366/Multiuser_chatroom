import socket
import ssl
import threading
import time
import os

host = '10.1.2.249'
port = 12345
context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE  # dev mode

# Wrap and connect socket securely
raw_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_client = context.wrap_socket(raw_client)
ssl_client.connect((host, port))
client = ssl_client

def receive():
    while True:
        try:
            msg = client.recv(1024).decode()
            if msg:
                print(msg)
        except:
            print("Disconnected from server.")
            break

def write():
    while True:
        msg = input()
        if msg == "/sendfile":
            filename = input("Enter file name to send: ")
            try:
                with open(filename, "rb") as f:
                    file_data = f.read()
            except FileNotFoundError:
                print("File not found!")
                continue
            filesize = len(file_data)
            client.send(f"/sendfile|{os.path.basename(filename)}|{filesize}".encode())
            time.sleep(1)
            client.sendall(file_data)
            print("File sent successfully!")
        else:
            try:
                client.send(msg.encode())
            except:
                break

threading.Thread(target=receive).start()
threading.Thread(target=write).start()
