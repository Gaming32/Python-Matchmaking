import _thread
mutex = _thread.allocate_lock()
_print = print
def print(*vals, **kwargs):
    mutex.acquire()
    res = _print(*vals, **kwargs)
    mutex.release()
    return res