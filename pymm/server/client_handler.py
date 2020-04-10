import sys
import _thread
from netsc.server import Server, socket
from netsc.struct import return2data
from ..util import error_info, dict_to_list
from .printer import print


class _ClientHandler:
    def __init__(self, parent):
        self.parent = parent
        self.thread = _thread.get_ident()
    def _verbose(self, *values, **kwargs):
        if self.parent.verbose:
            print(*values, **kwargs)
    def disconnect(self):
        self._verbose('client', self.parent.sock.getpeername(), 'disconecting...')
        self.parent.sock.close()
        self._verbose('thread', hex(self.thread), 'exited')
        _thread.exit()
        return False
    def _test_errors(self, error=True):
        if error: raise ValueError('error raised')
        return 'done'

class ClientHandler(Server):
    def __init__(self, bind_addr=('', 0), sock_family=socket.AF_INET):
        self.sock_family, self.bind_addr = sock_family, bind_addr
        self.wrapped = _ClientHandler(self)
        if sys.version_info >= (3, 8) and socket.has_dualstack_ipv6():
            self.sock = socket.create_server(bind_addr, family=socket.AF_INET6, dualstack_ipv6=True)
        else:
            self.sock = socket.create_server(bind_addr, family=sock_family, dualstack_ipv6=False)
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