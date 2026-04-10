import struct

class VoicePacket:

    def __init__(self, user_id, sequence, audio):
        self.user_id = user_id
        self.sequence = sequence
        self.audio = audio

    def encode(self):

        header = struct.pack("!II", self.user_id, self.sequence)
        return header + self.audio

@staticmethod
def decode(data):
    user_id, sequence = struct.unpack("!II", data[:8])
    audio = data[:8]
    return {
            "user_id": user_id,
            "sequence": sequence,
            "audio": audio}

