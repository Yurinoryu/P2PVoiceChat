import socket
import threading
import time

from common.connection import Connection
from common.packets import CHAT, IMAGE, JOIN, JOIN_ACCEPT, PING, ROOM_STATE, TALKING, create_packet


class Client:
    def __init__(self, host, username, tcp_port, session_key):
        self.sock = socket.socket()
        self.sock.connect((host, tcp_port))
        self.conn = Connection(self.sock)
        self.host = host
        self.username = username
        self.user_id = None
        self.session_key = session_key
        self.handlers = {
            "connected": [],
            "chat": [],
            "image": [],
            "room_state": [],
            "talking": [],
            "status": [],
        }
        self.conn.on(JOIN_ACCEPT, self._join_ok)
        self.conn.on(CHAT, self._chat)
        self.conn.on(IMAGE, self._image)
        self.conn.on(ROOM_STATE, self._room_state)
        self.conn.on(TALKING, self._talking)

    def on(self, event_name, handler):
        self.handlers.setdefault(event_name, []).append(handler)

    def start(self):
        self.conn.start()
        self.conn.send(
            create_packet(
                JOIN,
                {
                    "username": self.username,
                    "session_key": self.session_key,
                },
            )
        )
        threading.Thread(target=self._ping, daemon=True).start()

    def close(self):
        self.conn.close()

    def send_chat(self, msg):
        self.conn.send(create_packet(CHAT, {"message": msg}))

    def send_image(self, filename, image_data):
        self.conn.send(
            create_packet(
                IMAGE,
                {
                    "filename": filename,
                    "image_data": image_data,
                },
            )
        )

    def send_talking(self, talking):
        self.conn.send(create_packet(TALKING, {"talking": bool(talking)}))

    def _join_ok(self, conn, packet):
        self.user_id = packet["data"]["user_id"]
        self._emit("connected", {"user_id": self.user_id})
        self._emit("status", {"message": f"Connected to {self.host}"})

    def _chat(self, conn, packet):
        self._emit("chat", packet["data"])

    def _image(self, conn, packet):
        self._emit("image", packet["data"])

    def _room_state(self, conn, packet):
        self._emit("room_state", packet["data"])

    def _talking(self, conn, packet):
        self._emit("talking", packet["data"])

    def _emit(self, event_name, payload):
        for handler in self.handlers.get(event_name, []):
            handler(payload)

    def _ping(self):
        while self.conn.running:
            time.sleep(5)
            try:
                self.conn.send(create_packet(PING))
            except Exception:
                break
