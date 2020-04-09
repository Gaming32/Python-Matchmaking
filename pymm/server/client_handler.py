import _thread
from netsc.server import Server, socket
from netsc.struct import return2data
from ..util import error_info, dict_to_list


class _ClientHandler:
    def __init__(self, parent):
        self.parent = parent
    def _test_errors(self, error=True, exit=False):
        if error: raise ValueError('error raised')
        if exit:
            if self.parent.verbose:
                print('thread exit')
            _thread.exit()
        return 'done'

class ClientHandler(Server):
    def __init__(self, bind_addr=('', 0), sock_family=socket.AF_INET, sock_type=socket.SOCK_STREAM, sock_proto=0):
        self.sock_family, self.sock_type, self.sock_proto, self.bind_addr = sock_family, sock_type, sock_proto, bind_addr
        super().__init__(_ClientHandler(self))
        self.verbose = False
    def poll(self):
        try: value = super().poll()
        except Exception as e:
            e_info = error_info(e)
            network_e_info = ('error', e_info[0], e_info[1], dict_to_list(e_info[2]))
            self.sock.send(return2data(network_e_info))
            value = e_info
        return value


def poller(client_handler:ClientHandler, verbose=False):
    client_handler.verbose = verbose
    while True:
        client_handler.poll()


if __name__ == '__main__':
    ch = ClientHandler(('', 12345))
    print('ready')
    print(ch.accept(), 'connected')
    while True:
        value = ch.poll()
        print('value: %r' % (value,))
        if value == 'exit': break