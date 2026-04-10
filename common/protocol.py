import json

class PacketEncoder:

    @staticmethod
    def encode(packet):
        data = json.dumps(packet).encode()

        length = len(data).to_bytes(4, 'big')

        return length + data

class PacketDecoder:

    def __init__(self):
        self.buffer = b""

    def feed(self, data):
        self.buffer += data

        packets = []

        while True:
            if len(self.buffer) < 4:
                break

            length = int.from_bytes(self.buffer[:4], 'big')

            if len(self.buffer < 4 + length: 
                break

            payload = self.buffer[4:4+length]

            self.buffer = self.buffer[4+length:]

            packets.append(json.load(payload.decode()))

        return packets
