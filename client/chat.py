import socket
import threading
from common.protocol import encode_packet, decode_packet
from common.config import TCP_PORT

def listen(sock):
    while True: 
        data = sock.recv(4096)
        if not data:
            break

        msg = decode_packet(data.decode())
        print(f"{msg['user']}: {msg['message']}")

def start_chat(username, host):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, TCP_PORT))

    threading.THREAD(target=listen, args=(sock,), daemon=True).start()

    while True:
        text = input("> ")

        packet = {
                "type": "chat",
                "user": username,
                "message": text
                }
        sock.sendall(encode_packet(packet))
