import socket
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext
import time
import cv2
import pickle
import struct
import os

host = '192.168.130.243'
port = 12345
video_port = 12347


import ssl  


context = ssl.create_default_context()
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE 
raw_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ssl_client = context.wrap_socket(raw_client)
ssl_client.connect((host, port))
client = ssl_client  


def receive_messages():
    while True:
        try:
            msg = client.recv(1024).decode().strip()
            if msg:
                chat_display.config(state='normal')
                chat_display.insert(tk.END, msg + '\n')
                chat_display.config(state='disabled')
                chat_display.yview(tk.END)
        except Exception as e:
            chat_display.config(state='normal')
            chat_display.insert(tk.END, f"⚠️ Disconnected: {e}\n")
            chat_display.config(state='disabled')
            break

def send_message():
    msg = msg_entry.get().strip()
    if msg:
        if msg.startswith("/playvideo"):
            filepath = msg.split(" ", 1)[1] if len(msg.split(" ", 1)) > 1 else filedialog.askopenfilename()
            if filepath and os.path.exists(filepath):
                threading.Thread(target=stream_video_file, args=(filepath,), daemon=True).start()
            else:
                chat_display.config(state='normal')
                chat_display.insert(tk.END, "❌ Invalid video file.\n")
                chat_display.config(state='disabled')
        elif msg == "/watch":
            threading.Thread(target=watch_stream, daemon=True).start()
        else:
            try:
                client.send(msg.encode())
            except Exception as e:
                chat_display.config(state='normal')
                chat_display.insert(tk.END, f"❌ Error: {e}\n")
                chat_display.config(state='disabled')
        msg_entry.delete(0, tk.END)

def send_file():
    filename = filedialog.askopenfilename()
    if not filename:
        return
    try:
        with open(filename, "rb") as f:
            file_data = f.read()
        filesize = len(file_data)
        client.send(f"/sendfile|{os.path.basename(filename)}|{filesize}".encode())
        time.sleep(0.1)
        client.sendall(file_data)
        chat_display.config(state='normal')
        chat_display.insert(tk.END, "✅ File sent successfully!\n")
        chat_display.config(state='disabled')
        chat_display.yview(tk.END)
    except Exception as e:
        chat_display.config(state='normal')
        chat_display.insert(tk.END, f"❌ Error: {e}\n")
        chat_display.config(state='disabled')

def stream_video():
    filepath = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
    if filepath and os.path.exists(filepath):
        threading.Thread(target=stream_video_file, args=(filepath,), daemon=True).start()
    else:
        chat_display.config(state='normal')
        chat_display.insert(tk.END, "❌ Invalid video file.\n")
        chat_display.config(state='disabled')

def stream_video_file(filepath):
    video_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        video_client.connect((host, video_port))
        video_client.send("sender".ljust(10).encode())
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            raise Exception("Cannot open video file")
        chat_display.config(state='normal')
        chat_display.insert(tk.END, f"▶️ Streaming video: {os.path.basename(filepath)}\n")
        chat_display.config(state='disabled')
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (640, 480))  # Optimize frame size
            data = pickle.dumps(frame)
            message = struct.pack("Q", len(data)) + data
            try:
                video_client.sendall(message)
            except:
                break
            time.sleep(1/30)  # 30 FPS
        cap.release()
        chat_display.config(state='normal')
        chat_display.insert(tk.END, "✅ Video streaming stopped.\n")
        chat_display.config(state='disabled')
    except Exception as e:
        chat_display.config(state='normal')
        chat_display.insert(tk.END, f"❌ Streaming error: {e}\n")
        chat_display.config(state='disabled')
    finally:
        video_client.close()

def watch_stream():
    stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        stream_socket.connect((host, video_port))
        stream_socket.send("viewer".ljust(10).encode())
        chat_display.config(state='normal')
        chat_display.insert(tk.END, "📺 Watching live stream...\n")
        chat_display.config(state='disabled')
        data = b''
        payload_size = struct.calcsize("Q")
        while True:
            while len(data) < payload_size:
                packet = stream_socket.recv(4096)
                if not packet:
                    return
                data += packet
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            while len(data) < msg_size:
                packet = stream_socket.recv(4096)
                if not packet:
                    return
                data += packet
            frame_data = data[:msg_size]
            data = data[msg_size:]

            frame = pickle.loads(frame_data)
            cv2.imshow("Live Video Stream", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    except Exception as e:
        chat_display.config(state='normal')
        chat_display.insert(tk.END, f"❌ Stream error: {e}\n")
        chat_display.config(state='disabled')
    finally:
        stream_socket.close()
        cv2.destroyAllWindows()
        chat_display.config(state='normal')
        chat_display.insert(tk.END, "🛑 Stopped watching stream.\n")
        chat_display.config(state='disabled')

# GUI setup
app = tk.Tk()
app.title("Chat Client with Streaming")
app.geometry("500x500")

chat_display = scrolledtext.ScrolledText(app, state='disabled')
chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

msg_entry = tk.Entry(app)
msg_entry.pack(padx=10, pady=5, fill=tk.X)
msg_entry.bind("<Return>", lambda e: send_message())

btn_frame = tk.Frame(app)
btn_frame.pack(pady=5)

send_btn = tk.Button(btn_frame, text="Send", command=send_message)
send_btn.grid(row=0, column=0, padx=5)

file_btn = tk.Button(btn_frame, text="Send File", command=send_file)
file_btn.grid(row=0, column=1, padx=5)

stream_btn = tk.Button(btn_frame, text="Stream Video", command=stream_video)
stream_btn.grid(row=0, column=2, padx=5)

watch_btn = tk.Button(btn_frame, text="Watch Stream", command=lambda: threading.Thread(target=watch_stream, daemon=True).start())
watch_btn.grid(row=0, column=3, padx=5)

threading.Thread(target=receive_messages, daemon=True).start()

app.mainloop()