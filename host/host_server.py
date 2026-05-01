import socket
import threading
import time

from common.connection import Connection
from common.config import CLEANUP_INTERVAL, CLIENT_IDLE_TIMEOUT, HOST_BIND, MAX_CHAT_LENGTH, MAX_USERNAME_LENGTH, SOCKET_BACKLOG, TCP_PORT
from common.packets import CHAT, IMAGE, JOIN, JOIN_ACCEPT, PING, ROOM_STATE, TALKING, create_packet


class HostServer:
    def __init__(self, session_key):
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((HOST_BIND, TCP_PORT))
        self.server.listen(SOCKET_BACKLOG)
        self.session_key = session_key
        self.clients = {}
        self.last_seen = {}
        self.next_id = 1
        self.lock = threading.Lock()

    def start(self):
        threading.Thread(target=self._cleanup, daemon=True).start()
        print(f"Host server started on tcp://{HOST_BIND}:{TCP_PORT}")

        while True:
            sock, addr = self.server.accept()
            conn = Connection(sock, addr)
            conn.on(JOIN, self._handle_join)
            conn.on(CHAT, self._handle_chat)
            conn.on(IMAGE, self._handle_image)
            conn.on(TALKING, self._handle_talking)
            conn.on(PING, self._handle_ping)
            conn.start()

    def _handle_join(self, conn, packet):
        if packet["data"].get("session_key") != self.session_key:
            conn.close()
            return

        username = (packet["data"].get("username") or "Guest").strip()[:MAX_USERNAME_LENGTH]
        if not username:
            username = "Guest"

        with self.lock:
            uid = self.next_id
            self.next_id += 1
            conn.user_id = uid
            conn.username = username
            self.clients[uid] = conn
            self.last_seen[uid] = time.time()

        conn.send(create_packet(JOIN_ACCEPT, {"user_id": uid}))
        self._broadcast_room_state()

    def _handle_chat(self, conn, packet):
        uid = getattr(conn, "user_id", None)
        if not uid:
            return

        self._broadcast(
            create_packet(
                CHAT,
                {
                    "user_id": uid,
                    "username": getattr(conn, "username", f"User {uid}"),
                    "message": packet["data"].get("message", "")[:MAX_CHAT_LENGTH],
                },
            )
        )

    def _handle_image(self, conn, packet):
        uid = getattr(conn, "user_id", None)
        if not uid:
            return

        self._broadcast(
            create_packet(
                IMAGE,
                {
                    "user_id": uid,
                    "username": getattr(conn, "username", f"User {uid}"),
                    "filename": packet["data"].get("filename", "image"),
                    "image_data": packet["data"].get("image_data", ""),
                },
            )
        )

    def _handle_talking(self, conn, packet):
        uid = getattr(conn, "user_id", None)
        if not uid:
            return

        self._broadcast(
            create_packet(
                TALKING,
                {
                    "user_id": uid,
                    "talking": bool(packet["data"].get("talking")),
                },
            )
        )

    def _handle_ping(self, conn, packet):
        uid = getattr(conn, "user_id", None)
        if uid:
            self.last_seen[uid] = time.time()

    def _cleanup(self):
        while True:
            time.sleep(CLEANUP_INTERVAL)
            now = time.time()
            stale_users = []

            with self.lock:
                for uid, last_seen in list(self.last_seen.items()):
                    conn = self.clients.get(uid)
                    if conn is None or not conn.running or now - last_seen > CLIENT_IDLE_TIMEOUT:
                        stale_users.append(uid)

                if stale_users:
                    for uid in stale_users:
                        conn = self.clients.pop(uid, None)
                        self.last_seen.pop(uid, None)
                        if conn is not None:
                            conn.close()

            if stale_users:
                self._broadcast_room_state()

    def _broadcast_room_state(self):
        with self.lock:
            users = [
                {
                    "user_id": uid,
                    "username": getattr(conn, "username", f"User {uid}"),
                }
                for uid, conn in self.clients.items()
                if conn.running
            ]

        self._broadcast(create_packet(ROOM_STATE, {"users": users}))

    def _broadcast(self, packet):
        with self.lock:
            recipients = list(self.clients.items())

        stale_users = []
        for uid, conn in recipients:
            try:
                conn.send(packet)
            except Exception:
                stale_users.append(uid)

        if stale_users:
            with self.lock:
                for uid in stale_users:
                    conn = self.clients.pop(uid, None)
                    self.last_seen.pop(uid, None)
                    if conn is not None:
                        conn.close()

            self._broadcast_room_state()
