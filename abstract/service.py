from abstract.bases.importer import threading

from abstract.bases.exceptions import *
from abstract.bases.log import LOG


class Service:
    def __init__(self, func, service_name, auto_restart=False):
        def decorated(*args, **kwargs):
            while not self.stop_flag.is_set():
                try:
                    func(*args, **kwargs)
                except SendFailure as error:
                    LOG.WAR(error)
                except Exception as error:
                    LOG.ERR(error)
                    if self.auto_restart:
                        LOG.INF(f'Service {self} automatically restarting...')
                        continue
            else:
                self.stop_flag.clear()
        self.thread = threading.Thread()
        self.args = None
        self.kwargs = None
        self.func = decorated
        self.service_name: str = service_name
        self.auto_restart: bool = auto_restart
        self.stop_flag = threading.Event()

    def __str__(self):
        return self.service_name

    def __repr__(self):
        return f'<Service {self.service_name}> at {hex(id(self))}'

    def start(self, *args, **kwargs):
        assert self.func
        assert not self.thread.is_alive()
        LOG.INF(f'Service {self} starting...')
        self.args = args
        self.kwargs = kwargs
        self.thread = threading.Thread(target=self.func, args=self.args, kwargs=self.kwargs)
        self.thread.start()
        LOG.INF(f'Service {self} started.')

    def stop(self, timeout=None):
        LOG.INF(f'Service {self} stopping...')
        self.stop_flag.set()
        self.thread.join(timeout)
        LOG.INF(f'Service {self} stopped.')

    def is_alive(self):
        return self.thread.is_alive()
