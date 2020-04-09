import _thread
from .client_handler import ClientHandler, poller as client_poller

def start(addr=('', 0)):
    print('started succesfully')
    while True:
        print('accepting connection...')
        handler = ClientHandler(addr)
        newconn = handler.accept()
        print(newconn, 'connected')
        _thread.start_new_thread(client_poller, (handler,))