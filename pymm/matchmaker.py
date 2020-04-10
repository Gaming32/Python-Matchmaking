from netsc.client import Client

class Matchmaker(Client):
    def __init__(self):
        super().__init__(None)
    def disconnect(self) -> bool:
        try: value = self._message('disconnect')
        except ConnectionAbortedError: value = True
        if not value: raise ConnectionError('could not disconnect')
        return value