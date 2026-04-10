import threading

from common.protocol import PacketEncoder, PacketDecoder

class Connection:

    def __init__(self, sock, address=None):
        self.sock = sock
        self.address = address
        self.decoder = PacketDecoder()
        self.handlers = {}
        self.running = False
        self.send_lock = threading.Lock()

    # Handler Registration

    def on(self, packet_type, handler):
        self.handlers[packet_type] = handler

    def start(self):
        self.running = True
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def send(self, packet):
        data = PacketEncoder.encode(packet)

        with self.send_lock:

            try:
                self.sock.sendall(data)
            except:
                self.close()

    def _recv_loop(self):

        while self.running:

            try:
                data = self.sock.recv(4096)

                if not data:
                    break

                packets = self.decoder.feed(data)

                for p in packets:
                    self._dispatch(p)

            except:
                break

        self.close()


    def _dispatch(self, packet):
        handler = self.handlers.get(packet.get("type"))
        if handler:
            handler(self, packet)

    def close(self):
        self.running = False
        try:
            self.sock.close()
        except:
            pass
