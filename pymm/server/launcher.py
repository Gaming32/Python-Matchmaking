import sys, os
import argparse
import _thread, time, shlex, socket, configparser
from .client_handler import ClientHandler, poller as client_poller
from .printer import print


def socket_generator(bind_addr, sock_family=socket.AF_INET):
    if sys.version_info >= (3, 8) and socket.has_dualstack_ipv6():
        sock = socket.create_server(bind_addr, family=socket.AF_INET6, dualstack_ipv6=True)
    else:
        sock = socket.socket(sock_family)
        sock.bind(bind_addr)
    return sock


def telnet_recv(sock, password=False):
    r = b''
    b = sock.recv(1)
    while b != b'\x00' and b != b'\r' and b != b'':
        # print(b)
        if not password: sock.send(b if b != b'\x7f' else b'\b\x7f')
        if b != b'\x7f':
            r += b
        else:
            r = r[:-1]
        b = sock.recv(1)
    sock.send(b'\r\n')
    return r.decode().rstrip()

def input_loop(addr=('', 0), backlog=0, family=socket.AF_INET, *, main_addr=None, allow_connections=None, password=None):
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
        sock.send(b'\xff\xfd\x22')
        if password is not None:
            sock.send(b'\xff\xfe\x01')
            sock.send(b'\xff\xfb\x01')
            some_data = sock.recv(1024)
            while True:
                sock.send('Password: '.encode('utf-8'))
                # sock.send(b'\xff\xfc\x01')
                recved_password = telnet_recv(sock, True)
                # sock.send(b'\xff\xfd\x01')
                some_data = sock.recv(1024)
                # print(recved_password)
                if recved_password != password:
                    sock.send('That password is incorrect.\r\n'.encode('utf-8'))
                else: break
        while True:
            sock.send('> '.encode('utf-8'))
            command = shlex.split(telnet_recv(sock))
            if not command: continue
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
    exit_threads(force, main_addr, allow_connections)


def exit_threads(force=False, shut_down_addr=None, allow_connections=None):
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


def start(addr=('', 0), backlog=100, input_addr=('', 0), input_backlog=0, control_password=None, verbose=False):
    threads = []
    allow_connections = [True]
    _thread.start_new_thread(input_loop,
                            (input_addr, input_backlog),
                            dict(main_addr=addr, allow_connections=allow_connections, password=control_password))
    sock = socket_generator(addr)
    sock.listen(backlog)

    try:
        print('listening for connections with a backlog of', backlog)
        print('started succesfully')
        while True:
            handler = ClientHandler(None)
            print('accepting connection on %s...' % (sock.getsockname(),))
            (newsock, newaddr) = sock.accept()
            handler.sock = newsock
            thread_id = _thread.start_new_thread(poller_wrapper, (handler, verbose, threads))
            print(newaddr, 'connected on thread', hex(thread_id))
            threads.append((newaddr, thread_id))
            if not allow_connections[0]: break

    except KeyboardInterrupt:
        print('stopping...')
        sock.close()
        force = allow_connections[1]
        if not force:
            print('shutting down threads...')
            prev_threads = []
            def print_users():
                nonlocal prev_threads
                if threads == prev_threads: return
                print('waiting for the following users to disconnect:')
                for (addr, thread) in threads:
                    print('   ', addr, 'on thread', hex(thread))
                prev_threads = threads[:]
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
    default_config_directory = '%APPDATA%\\python-matchmaking\\config'
else:
    default_config_directory = '~/.pymm/config'
default_config_directory_absolute = os.path.expandvars(os.path.expanduser(default_config_directory))

argument_types = {
    'verbose': int,
    'port': int,
    'connection_backlog': int,
    'control_port': int,
    'control_connection_backlog': int,
}

configparser_types = {
    str: configparser.ConfigParser.get,
    int: configparser.ConfigParser.getint,
    float: configparser.ConfigParser.getfloat,
    bool: configparser.ConfigParser.getboolean,
}

argument_parser = argparse.ArgumentParser(prog='%s -m pymm.server' % shlex.quote(get_python_path()))
argument_parser.add_argument('-~', '--prepare', action='store_true')
argument_parser.add_argument('-c', '--config-directory', metavar='PATH', default=default_config_directory_absolute,
    help='Default value: %s' % default_config_directory.replace('%', '%%'))
argument_parser.add_argument('-v', '--verbose', default=0, action='count')
argument_parser.add_argument('-p', '--port', type=int)
argument_parser.add_argument('-i', '--bind-interface', metavar='INTERFACE', default='')
argument_parser.add_argument('-b', '--connection-backlog', metavar='BACKLOG', type=int, default=100,
    help='Default value: 100')
argument_parser.add_argument('--control-port', type=int, metavar='PORT')
argument_parser.add_argument('--control-bind-interface', metavar='INTERFACE', default='')
argument_parser.add_argument('--control-connection-backlog', metavar='CONNECTIONS', type=int, default=0)
argument_parser.add_argument('--control-password', metavar='PASSWORD')
argument_parser.add_argument('--auth-code', action='append', metavar='CODE', dest='authcodes', default=[])

def main(argv=sys.argv[1:]):
    args = argument_parser.parse_args(argv)
    print('starting...')
    configfile_dict = {
        'conf.cfg': os.path.join(args.config_directory, 'conf.cfg'),
        'auth.txt': os.path.join(args.config_directory, 'auth.txt'),
    }
    if not os.path.exists(args.config_directory):
        os.makedirs(args.config_directory)
        open(configfile_dict['conf.cfg'], 'w')
        open(configfile_dict['auth.txt'], 'w')
        print('created config directory at', shlex.quote(args.config_directory))

    with open(configfile_dict['conf.cfg']) as fp:
        configdata = '[DEFAULT]\n'
        configdata += fp.read()
    configfile = configparser.ConfigParser()
    configfile.read_string(configdata)

    for name in configfile[configparser.DEFAULTSECT]:
        argname = name.replace('-', '_')
        argtype = argument_types.get(argname, str)
        getfunc = configparser_types.get(argtype, configparser.ConfigParser.get)
        args.__dict__[argname] = getfunc(configfile, configparser.DEFAULTSECT, name)
    # args.__dict__.update({
    #     x.replace('-', '_'): configfile.getint(configparser.DEFAULTSECT, x)
    #     for x in configfile[configparser.DEFAULTSECT]
    # })
    del configfile, configdata
    args.authcodes.extend(x.strip() for x in open(configfile_dict['auth.txt']))
    print('ready to start')

    if args.prepare: return
    start((args.bind_interface, args.port), args.connection_backlog,
          (args.control_bind_interface, args.control_port), args.control_connection_backlog,
          args.control_password, args.verbose)


if __name__ == '__main__': main()