import socket
from common.voice_packet import VoicePacket
from common.config import UDP_PORT

class VoiceRouter:

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", UDP_PORT))
        self.clients = {}
        self.seq = {}

    def start(self):
        while True:
            data, addr = self.sock.recvfrom(4096)
            p = VoicePacket.decode(data)

            uid = p["user_id"]
            seq = p["sequence"]

            self.clients[uid] = addr
            if seq <= self.seq.get(uid, -1):
                continue
            self.seq[uid] = seq

            for u, a in self.clients.items():
                if u != uid:
                    self.sock.sendto(data, a)
