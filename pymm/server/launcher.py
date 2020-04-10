import sys
import _thread, time, shlex, socket
from .client_handler import ClientHandler, poller as client_poller
from .printer import print

def input_loop(threads, addr=('', 0), backlog=0, family=socket.AF_INET):
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
            command, *args = shlex.split(sock.recv(1024).decode('utf-8'))
            if command == 'exit':
                if '--force' in args or '-f' in args:
                    force = True
                sock.close()
                do_exit = True
                break
            elif command == 'disconnect':
                sock.close()
        if do_exit: break
    server.close()
    print('shutting down threads...')
    exit_threads(force)

def exit_threads(threads, force=False):
    def print_users():
        print('waiting for the following users to disconnect:', end='')
        for (addr, thread) in threads:
            print('   ', addr, 'on thread', thread)
    if not force:
        while threads:
            print_users()
            time.sleep(0.5)
    _thread.interrupt_main()

def start(addr=('', 0), input_addr=('', 0), input_backlog=0, verbose=False):
    threads = []
    input_loop(threads, input_addr, input_backlog)
    print('started succesfully')
    while True:
        handler = ClientHandler(addr)
        print('accepting connection on %s...' % handler.sock.getsockname())
        newconn = handler.accept()
        thread_id = _thread.start_new_thread(client_poller, (handler, verbose))
        print(newconn, 'connected on thread', hex(thread_id))
        threads.append((newconn, thread_id))

def get_python_path():
    import os
    path = os.environ['PATH'].split(os.pathsep)
    relative_path = [os.path.relpath(sys.executable, x) for x in path]
    shortest = min(relative_path, key=(lambda x: len(x.split(os.sep))))
    return shortest

def main(argv=sys.argv[1:]):
    if '-h' in argv or '--help' in argv:
        print('usage: %s -m pymm.server' % get_python_path(),
              '[-v|--verbose]',
              '[server_port] [server_bind_addr]',
              '[command_port] [command_bind_addr]',
              '[command_connection_backlog]')
        exit()
    verbose = 0
    pos_args = []
    for arg in argv:
        if arg[0] == '-':
            if arg == '-v' or arg == '--verbose':
                verbose += 1
            else:
                print('unknown argument:', arg)
                sys.exit(1)
        else:
            pos_args.append(arg)
    if len(pos_args) > 5:
        print('additional args passed:', ', '.join(pos_args))
        sys.exit(1)
    if len(pos_args) >= 1:
        pos_args[1] = int(pos_args[0])
    if len(pos_args) >= 3:
        pos_args[3] = int(pos_args[2])
    if len(pos_args) >= 5:
        pos_args[4] = int(pos_args[4])
    result = [0, '', 0, '', 0]
    for (ix, value) in pos_args:
        result[ix] = value
    try: start(tuple(reversed(result[0:2])), tuple(reversed(result[2:4])), result[4], bool(verbose))
    except KeyboardInterrupt:
        print('stopping...')

if __name__ == '__main__': main()