import socket
import threading
import time

from common.connection import Connection
from common.config import TCP_PORT, SESSION_KEY
from common.packets import *

class Client:
    def __init__(self, host, username):
        self.sock = socket.socket()
        self.sock.connect((host, TCP_PORT))
        self.conn = Connection(self.sock)
        self.username = username
        self.user_id = None
        self.conn.on(JOIN_ACCEPT, self._join_ok)
        self.conn.on(CHAT, self._chat)

    def start(self):
        self.conn.start()
        self.conn.send(create_packet(JOIN, {
            "username": self.username,
            "session_key": SESSION_KEY}))
        threading.Thread(target=self._ping, daemon=True).start()

    def _join_ok(self, conn, packet):
        self.user_id = packet["data"]["user_id"]
        print("Connected", self.user_id)

    def _chat(self, conn, packet):
        print(packet["data"]["message"])

    def send_chat(self, msg):
        self.conn.send(create_packet(CHAT, {"message": msg}))

    def _ping(self):
        while True:
            time.sleep(5)
            self.conn.send(create_packet(PING))

