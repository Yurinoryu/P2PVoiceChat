JOIN = "join"
JOIN_ACCEPT = "join_accept"

CHAT = "chat"

PING = "ping"
PONG = "pong"

def create_packet(packet_type, data=None):
    return {"type": packet_type, "data": data or {}}

