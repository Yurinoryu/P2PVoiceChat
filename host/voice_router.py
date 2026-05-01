import socket

from common.voice_packet import VoicePacket
from common.config import HOST_BIND, UDP_PORT


class VoiceRouter:
    def __init__(self, session_key):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST_BIND, UDP_PORT))
        self.session_key = session_key
        self.clients = {}
        self.seq = {}

    def start(self):
        print(f"Voice router started on udp://{HOST_BIND}:{UDP_PORT}")
        while True:
            data, addr = self.sock.recvfrom(4096)
            try:
                packet = VoicePacket.decode(data, self.session_key)
            except ValueError:
                continue

            uid = packet["user_id"]
            seq = packet["sequence"]

            self.clients[uid] = addr
            if seq <= self.seq.get(uid, -1):
                continue
            self.seq[uid] = seq

            stale_users = []
            for other_uid, other_addr in self.clients.items():
                if other_uid == uid:
                    continue
                try:
                    self.sock.sendto(data, other_addr)
                except OSError:
                    stale_users.append(other_uid)

            for stale_uid in stale_users:
                self.clients.pop(stale_uid, None)
                self.seq.pop(stale_uid, None)
