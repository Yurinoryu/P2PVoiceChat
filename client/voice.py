import socket
import threading
import sounddevice as sd
import numpy as np
from common.voice_packet import VoicePacket
from common.opus_codec import OpusCodec
from common.config import UDP_PORT, AUDIO_RATE

class VoiceClient:
    def __init__(self, host, uid):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.uid = uid
        self.codec = OpusCodec()
        self.seq = 0
        self.ptt = False

    def start(self):
        threading.Thread(target=self._recv, daemon = True).start()
        self._capture()

    def _capture(self):
        def cb(indata, frames, time, status):
            if not self.ptt:
                return

            pcm = (indata * 32767).astype(np.int16).tobytes()
            encoded = self.codec.encode(pcm)

            pkt = VoicePacket(self.uid, self.seq, encoded)
            self.sock.sendto(pkt.encode(), (self.host, UDP_PORT))
            self.seq += 1

        with sd.InputStream(callback=cb, samplerate=AUDIO_RATE, channels=1):
            input("Press enter to quit")

    def _recv(self):
        while True:
            data, _ = self.sock.recvfrom(4096)
            p = VoicePacket.decode(data)

            pcm = self.codec.decode(p["audio"])
            audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32767

            sd.play(audio, AUDIO_RATE)
