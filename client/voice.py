import socket
import threading
import time
from collections import defaultdict, deque

from common.config import AUDIO_RATE, UDP_PORT
from common.opus_codec import OpusCodec
from common.voice_packet import VoicePacket

FRAME_SIZE = 960
MAX_BUFFERED_FRAMES = 8
VOICE_THRESHOLD = 0.025
VOICE_HANG_MS = 0.35

try:
    import numpy as np
except ImportError:
    np = None

try:
    import sounddevice as sd
except ImportError:
    sd = None


def check_voice_support():
    if np is None:
        return False, "Voice is unavailable because `numpy` is not installed."

    if sd is None:
        return False, "Voice is unavailable because `sounddevice` is not installed."

    try:
        OpusCodec()
    except Exception as exc:
        return False, f"Voice is unavailable because Opus could not start: {exc}"

    try:
        sd.check_input_settings(samplerate=AUDIO_RATE, channels=1, dtype="float32")
        sd.check_output_settings(samplerate=AUDIO_RATE, channels=1, dtype="float32")
    except Exception as exc:
        return False, f"Voice is unavailable because audio devices are not ready: {exc}"

    return True, "Voice is ready."


class VoiceClient:
    def __init__(self, host, uid, session_key, talking_callback, udp_port=UDP_PORT):
        ready, message = check_voice_support()
        if not ready:
            raise RuntimeError(message)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host = host
        self.uid = uid
        self.session_key = session_key
        self.talking_callback = talking_callback
        self.udp_port = udp_port
        self.codec = OpusCodec()
        self.seq = 0
        self.running = False
        self.stream_thread = None
        self.playback_lock = threading.Lock()
        self.playback_buffers = defaultdict(deque)
        self.local_talking = False
        self.last_voice_time = 0.0

    def start(self):
        if self.running:
            return

        self.running = True
        self._register_with_router()
        threading.Thread(target=self._recv, daemon=True).start()
        self.stream_thread = threading.Thread(target=self._run_audio, daemon=True)
        self.stream_thread.start()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except OSError:
            pass

    def _run_audio(self):
        def input_cb(indata, frames, time_info, status):
            if status:
                print(f"Input audio status: {status}")

            mono = indata[:, 0]
            level = float(np.sqrt(np.mean(np.square(mono))))
            now = time.time()

            if level >= VOICE_THRESHOLD:
                self.last_voice_time = now
                if not self.local_talking:
                    self.local_talking = True
                    self.talking_callback(True)

                pcm = (mono * 32767).astype(np.int16).tobytes()
                encoded = self.codec.encode(pcm)
                self._send_packet(encoded)
            elif self.local_talking and now - self.last_voice_time > VOICE_HANG_MS:
                self.local_talking = False
                self.talking_callback(False)

        def output_cb(outdata, frames, time_info, status):
            if status:
                print(f"Output audio status: {status}")

            mix = np.zeros((frames,), dtype=np.float32)

            with self.playback_lock:
                stale_users = []

                for user_id, buffered_frames in self.playback_buffers.items():
                    if buffered_frames:
                        mix += buffered_frames.popleft()

                    if not buffered_frames:
                        stale_users.append(user_id)

                for user_id in stale_users:
                    self.playback_buffers.pop(user_id, None)

            outdata[:, 0] = np.clip(mix, -1.0, 1.0)

        try:
            with sd.OutputStream(
                samplerate=AUDIO_RATE,
                channels=1,
                blocksize=FRAME_SIZE,
                dtype="float32",
                callback=output_cb,
            ):
                with sd.InputStream(
                    samplerate=AUDIO_RATE,
                    channels=1,
                    blocksize=FRAME_SIZE,
                    dtype="float32",
                    callback=input_cb,
                ):
                    while self.running:
                        time.sleep(0.1)
        finally:
            if self.local_talking:
                self.local_talking = False
                self.talking_callback(False)

    def _recv(self):
        while self.running:
            try:
                data, _ = self.sock.recvfrom(4096)
                packet = VoicePacket.decode(data, self.session_key)

                if packet["user_id"] == self.uid or not packet["audio"]:
                    continue

                pcm = self.codec.decode(packet["audio"])
                audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32767.0

                if audio.size != FRAME_SIZE:
                    if audio.size < FRAME_SIZE:
                        audio = np.pad(audio, (0, FRAME_SIZE - audio.size))
                    else:
                        audio = audio[:FRAME_SIZE]

                with self.playback_lock:
                    user_buffer = self.playback_buffers[packet["user_id"]]
                    if len(user_buffer) >= MAX_BUFFERED_FRAMES:
                        user_buffer.popleft()
                    user_buffer.append(audio)
            except OSError:
                break
            except Exception as exc:
                print(f"Voice receive error: {exc}")

    def _send_packet(self, encoded_audio):
        packet = VoicePacket(self.uid, self.seq, encoded_audio)
        self.sock.sendto(packet.encode(self.session_key), (self.host, self.udp_port))
        self.seq += 1

    def _register_with_router(self):
        silent_pcm = (np.zeros((FRAME_SIZE,), dtype=np.int16)).tobytes()
        self._send_packet(self.codec.encode(silent_pcm))
