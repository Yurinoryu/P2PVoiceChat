import base64
import json
import secrets
import subprocess

from common.config import TCP_PORT, UDP_PORT


def generate_session_key():
    return secrets.token_urlsafe(24)


def get_tailscale_host():
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""

    for line in result.stdout.splitlines():
        candidate = line.strip()
        if candidate:
            return candidate

    return ""


def create_invite(host, tcp_port=TCP_PORT, udp_port=UDP_PORT, session_key=None):
    session_key = session_key or generate_session_key()
    payload = {
        "version": 2,
        "network": "tailscale",
        "host": host,
        "tcp_port": tcp_port,
        "udp_port": udp_port,
        "session_key": session_key,
    }
    encoded = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(encoded).decode()


def parse_invite(code):
    decoded = base64.urlsafe_b64decode(code.encode())
    payload = json.loads(decoded.decode())
    return {
        "network": payload.get("network", "tailscale"),
        "host": payload["host"],
        "tcp_port": payload.get("tcp_port", TCP_PORT),
        "udp_port": payload.get("udp_port", UDP_PORT),
        "session_key": payload.get("session_key"),
    }
