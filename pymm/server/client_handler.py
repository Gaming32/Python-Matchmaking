from netsc.server import Server


class ClientHandler(Server):
    def __init__(self, bind_addr=('', 0), sock_family=socket.AF_INET, sock_type=socket.SOCK_STREAM, sock_proto=0):
        self.sock_family, self.sock_type, self.sock_proto, self.bind_addr = sock_family, sock_type, sock_proto, bind_addr
        super().__init__(self)
    def poll(self):
        try: value = super().poll()