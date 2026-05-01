import unittest

from client.invite import create_invite, parse_invite
from common.packets import CHAT, create_packet
from common.protocol import PacketDecoder, PacketEncoder
from common.voice_packet import VoicePacket


class InviteTests(unittest.TestCase):
    def test_invite_round_trip(self):
        invite = create_invite("100.64.0.1", tcp_port=51010, udp_port=51011, session_key="secret")
        parsed = parse_invite(invite)

        self.assertEqual(parsed["host"], "100.64.0.1")
        self.assertEqual(parsed["tcp_port"], 51010)
        self.assertEqual(parsed["udp_port"], 51011)
        self.assertEqual(parsed["session_key"], "secret")


class ProtocolTests(unittest.TestCase):
    def test_packet_encoder_and_decoder_round_trip(self):
        packet = create_packet(CHAT, {"message": "hello"})
        encoded = PacketEncoder.encode(packet)
        decoded = PacketDecoder().feed(encoded)

        self.assertEqual(decoded, [packet])

    def test_packet_decoder_handles_split_frames(self):
        packet = create_packet(CHAT, {"message": "split"})
        encoded = PacketEncoder.encode(packet)
        decoder = PacketDecoder()

        first = decoder.feed(encoded[:3])
        second = decoder.feed(encoded[3:])

        self.assertEqual(first, [])
        self.assertEqual(second, [packet])


class VoicePacketTests(unittest.TestCase):
    def test_voice_packet_round_trip(self):
        packet = VoicePacket(12, 7, b"pcm-data")
        encoded = packet.encode("voice-secret")
        decoded = VoicePacket.decode(encoded, "voice-secret")

        self.assertEqual(decoded["user_id"], 12)
        self.assertEqual(decoded["sequence"], 7)
        self.assertEqual(decoded["audio"], b"pcm-data")

    def test_voice_packet_rejects_short_payloads(self):
        with self.assertRaises(ValueError):
            VoicePacket.decode(b"short", "voice-secret")


if __name__ == "__main__":
    unittest.main()
