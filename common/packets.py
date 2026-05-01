JOIN = "join"
JOIN_ACCEPT = "join_accept"
ROOM_STATE = "room_state"

CHAT = "chat"
IMAGE = "image"
TALKING = "talking"

PING = "ping"
PONG = "pong"

def create_packet(packet_type, data=None):
    return {"type": packet_type, "data": data or {}}
