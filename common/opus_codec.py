import opuslib

class OpusCodec:
    def __init__(self, rate=48000, channels=1):
        self.encoder = opuslib.Encoder(rate, channels, opuslib.APPLICATION_AUDIO)
        self.decoder = opuslib.Decoder(rate, channels)

    def encode(self, pcm):
        return self.encoder.encode(pcm, 960)

    def decode(self, data):
        return self.decoder.decode(data, 960)
