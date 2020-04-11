import sys, os
import argparse
import _thread, time, shlex, socket
from .client_handler import ClientHandler, poller as client_poller
from .printer import print


def input_loop(threads, addr=('', 0), backlog=0, family=socket.AF_INET, *, main_addr=None, allow_connections=None):
    if main_addr is None: raise ValueError('main_addr must be specified')
    if allow_connections is None: raise ValueError('allow_connections must be passed')
    server = socket.socket(family)
    server.bind(addr)
    server.listen(backlog)
    print('listening for command connections on', server.getsockname(), 'with a backlog of', backlog)
    do_exit = False
    force = False
    while True:
        (sock, addr) = server.accept()
        print('command connection from', addr)
        while True:
            command = shlex.split(sock.recv(1024).decode('utf-8'))
            command, args = command[0], command[1:]
            if command == 'shutdown':
                if '--force' in args or '-f' in args:
                    force = True
                sock.close()
                do_exit = True
                break
            elif command == 'exit':
                sock.close()
                break
        if do_exit: break
    server.close()
    exit_threads(threads, force, main_addr, allow_connections)


def exit_threads(threads, force=False, shut_down_addr=None, allow_connections=None):
    if shut_down_addr is None: raise ValueError('shut_down_addr must be specified')
    if allow_connections is None: raise ValueError('allow_connections must be passed')
    allow_connections[0] = False
    allow_connections.append(force)
    _thread.interrupt_main()
    try:
        s = socket.socket()
        s.connect(('127.0.0.1', shut_down_addr[1]))
    except ConnectionError: pass


def poller_wrapper(handler, verbose, threads):
    addr = handler.sock.getpeername()
    try: client_poller(handler, verbose)
    except (ConnectionError, SystemExit): pass
    for (ix, (thread_addr, thread_id)) in enumerate(threads):
        if thread_addr == addr:
            print('connection', addr, 'on thread', hex(thread_id), 'disconnected')
            del threads[ix]
            break


def start(addr=('', 0), input_addr=('', 0), input_backlog=0, verbose=False):
    threads = []
    allow_connections = [True]
    _thread.start_new_thread(input_loop, (threads, input_addr, input_backlog), dict(main_addr=addr, allow_connections=allow_connections))
    print('started succesfully')
    while True:
        handler = ClientHandler(addr)
        print('accepting connection on %s...' % (handler.sock.getsockname(),))
        newconn = handler.accept()
        thread_id = _thread.start_new_thread(poller_wrapper, (handler, verbose, threads))
        print(newconn, 'connected on thread', hex(thread_id))
        threads.append((newconn, thread_id))
        if not allow_connections[0]: break

    print('shutting down threads...')
    force = allow_connections[1]
    prev_threads = []
    def print_users():
        nonlocal prev_threads
        if threads == prev_threads: return
        print('waiting for the following users to disconnect:')
        for (addr, thread) in threads:
            print('   ', addr, 'on thread', hex(thread))
        prev_threads = threads[:]
    if not force:
        while threads:
            print_users()
            time.sleep(0.5)
    print('threads shut down')


def get_python_path():
    path = os.environ['PATH'].split(os.pathsep) + [os.curdir]
    relative_path = (os.path.relpath(sys.executable, x) for x in path)
    shortest = min(relative_path, key=(lambda x: len(x.split(os.sep))))
    if os.sep in shortest:
        return os.path.abspath(shortest)
    return shortest


if 'win' in sys.platform:
    default_config_directory = '%APPDATA%\\pymm\\config'
else:
    default_config_directory = '~/.pymm/config'
default_config_directory_absolute = os.path.expandvars(os.path.expanduser(default_config_directory))

argument_parser = argparse.ArgumentParser(prog='%s -m pymm.server' % get_python_path())
argument_parser.add_argument('-~', '--prepare', action='store_true')
argument_parser.add_argument('-c', '--config-directory', metavar='PATH', default=default_config_directory_absolute,
    help='Default value: %s' % default_config_directory.replace('%', '%%'))
argument_parser.add_argument('-v', '--verbose', default=0, action='count')
argument_parser.add_argument('-p', '--port', type=int)
argument_parser.add_argument('-i', '--bind-interface', metavar='INTERFACE', default='')
argument_parser.add_argument('--control-port', type=int, metavar='PORT')
argument_parser.add_argument('--control-bind-interface', metavar='INTERFACE', default='')
argument_parser.add_argument('--control-connection-backlog', metavar='CONNECTIONS', type=int, default=0)

def main(argv=sys.argv[1:]):
    args = argument_parser.parse_args(argv)
    print('starting...')
    if not os.path.exists(args.config_directory):
        os.makedirs(args.config_directory)
    print('ready to start')
    if args.prepare: return
    try: start((args.bind_interface, args.port), (args.control_bind_interface, args.control_port),
        args.control_connection_backlog, args.verbose)
    except KeyboardInterrupt:
        print('stopping...')


if __name__ == '__main__': main()