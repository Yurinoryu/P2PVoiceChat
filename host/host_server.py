import socket
import threading
import time

from common.connection import Connection
from common.config import TCP_PORT, SESSION_KEY
from common.packets import *

class HostServer:

    def __init__(self):
        self.server = socket.socket()
        self.server.bind(("0.0.0.0", TCP_PORT))
        self.server.listen()
        self.clients = {}
        self.last_seen = {}
        self.next_id = 1
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._cleanup, daemon=True).start()
        print("Server Started")

        while True:
            sock, addr = self.server.accept()
            conn = Connection(sock, addr)
            conn.on(JOIN, self._handle_join)
            conn.on(CHAT, self._handle_chat)
            conn.on(PING, self._handle_ping)
            conn.start()

    def _handle_join(self, conn, packet):
        if packet["data"].get("session_key") != SESSION_KEY:
            return
        with self.lock:
            uid = self.next_id
            self.next_id += 1
            conn.user_id = uid
            self.clients[uid] = conn
            self.last_seen[uid] = time.time()

        conn.send(create_packet(JOIN_ACCEPT, {"user_id": uid}))

    def _handle_chat(self, conn, packet):
        uid = getattr(conn, "user_id", None)
        if not uid:
            return
        msg = packet["data"]["message"]

        for c in self.clients.values():
            c.send(create_packet(CHAT, {"user_id": uid, "message": msg}))

    def _handle_ping(self, conn, packet):
        uid = getattr(conn, "user_id", None)
        if uid:
            self.last_seen[uid] = time.time()

    def _cleanup(self):
        while True:
            time.sleep(5)
            now = time.time()
            for uid, t in list(self.last_seen.items()):
                if now - t > 15:
                    self.clients[uid].close()
                    del self.clients[uid]
                    del self.last_seen[uid]
