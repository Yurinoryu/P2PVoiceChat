import platform
import socket
import struct
import sys

from client.invite import get_tailscale_host
from client.voice import check_voice_support
from common.config import AUDIO_RATE, TCP_PORT, UDP_PORT
from common.opus_codec import DLL_PATH, OPUS_IMPORT_ERROR


def _port_open_for_bind(port, sock_type):
    sock = socket.socket(socket.AF_INET, sock_type)
    try:
        sock.bind(("127.0.0.1", port))
        return True, "available"
    except OSError as exc:
        return False, str(exc)
    finally:
        sock.close()


def get_runtime_diagnostics():
    voice_ready, voice_message = check_voice_support()
    tailscale_host = get_tailscale_host()
    tcp_ok, tcp_message = _port_open_for_bind(TCP_PORT, socket.SOCK_STREAM)
    udp_ok, udp_message = _port_open_for_bind(UDP_PORT, socket.SOCK_DGRAM)

    return {
        "app": "Voice Chat",
        "python_version": sys.version.split()[0],
        "python_bitness": struct.calcsize("P") * 8,
        "platform": platform.platform(),
        "audio_rate": AUDIO_RATE,
        "tailscale_host": tailscale_host or "not detected",
        "voice_ready": voice_ready,
        "voice_message": voice_message,
        "opus_dll_path": DLL_PATH,
        "opus_import_error": "" if OPUS_IMPORT_ERROR is None else str(OPUS_IMPORT_ERROR),
        "tcp_port": TCP_PORT,
        "tcp_port_available": tcp_ok,
        "tcp_port_message": tcp_message,
        "udp_port": UDP_PORT,
        "udp_port_available": udp_ok,
        "udp_port_message": udp_message,
    }


def format_runtime_diagnostics():
    info = get_runtime_diagnostics()
    lines = [
        f"App: {info['app']}",
        f"Python: {info['python_version']} ({info['python_bitness']}-bit)",
        f"Platform: {info['platform']}",
        f"Tailscale host: {info['tailscale_host']}",
        f"Audio rate: {info['audio_rate']}",
        f"Voice ready: {info['voice_ready']}",
        f"Voice status: {info['voice_message']}",
        f"Opus DLL: {info['opus_dll_path']}",
        f"Opus import error: {info['opus_import_error'] or 'none'}",
        f"TCP {info['tcp_port']}: {info['tcp_port_message']}",
        f"UDP {info['udp_port']}: {info['udp_port_message']}",
    ]
    return "\n".join(lines)
