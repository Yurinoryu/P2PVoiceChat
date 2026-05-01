import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.diagnostics import format_runtime_diagnostics
from common.opus_codec import OpusCodec
from common.voice_packet import VoicePacket


def main():
    print("== Runtime Diagnostics ==")
    print(format_runtime_diagnostics())
    print()

    codec = OpusCodec()
    payload = b"\x00\x00" * 960
    encoded = codec.encode(payload)
    decoded = codec.decode(encoded)
    packet = VoicePacket(1, 1, encoded)
    restored = VoicePacket.decode(packet.encode("smoke-key"), "smoke-key")

    assert restored["user_id"] == 1
    assert restored["sequence"] == 1
    assert restored["audio"] == encoded
    assert isinstance(decoded, (bytes, bytearray))
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
