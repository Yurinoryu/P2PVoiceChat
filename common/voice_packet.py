import struct
import hmac
import hashlib

MAC_SIZE = 16

class VoicePacket:

    def __init__(self, user_id, sequence, audio):
        self.user_id = user_id
        self.sequence = sequence
        self.audio = audio

    def encode(self, secret):

        header = struct.pack("!II", self.user_id, self.sequence)
        mac = hmac.new(secret.encode("utf-8"), header + self.audio, hashlib.sha256).digest()[:MAC_SIZE]
        return header + mac + self.audio

    @staticmethod
    def decode(data, secret):
        if len(data) < 8 + MAC_SIZE:
            raise ValueError("Voice packet too short")
        user_id, sequence = struct.unpack("!II", data[:8])
        mac = data[8:8 + MAC_SIZE]
        audio = data[8 + MAC_SIZE:]
        expected = hmac.new(secret.encode("utf-8"), data[:8] + audio, hashlib.sha256).digest()[:MAC_SIZE]
        if not hmac.compare_digest(mac, expected):
            raise ValueError("Invalid voice packet authentication tag")
        return {
                "user_id": user_id,
                "sequence": sequence,
                "audio": audio}
