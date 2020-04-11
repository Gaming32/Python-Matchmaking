from netsc.client import Client
from .util import error_from_info, list_to_dict

class Matchmaker(Client):
    def __init__(self):
        super().__init__(None)
    def _message(self, name, args=(), kwargs={}):
        val = super()._message(name, args=args, kwargs=kwargs)
        if isinstance(val, tuple) and val[0] == 'error':
            info = list(val[1:])
            info[2] = list_to_dict(info[2])
            raise error_from_info(info) from None
        return val
    def disconnect(self) -> bool:
        try: value = self._message('disconnect')
        except ConnectionAbortedError: value = True
        if not value: raise ConnectionError('could not disconnect')
        return value