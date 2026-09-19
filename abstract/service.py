from abstract.bases.importer import threading, time
from typing import Callable

from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.bases.custom_thread import CustomThread


class Service:
    def __init__(self, func: Callable, service_name: str, loop_delay: int | float, auto_restart=False):
        def decorated(*args, **kwargs):
            while not self.stop:
                try:
                    func(*args, **kwargs)
                except SendFailure as error:
                    LOG.WAR(error)
                except Exception as error:
                    LOG.ERR(error)
                    if self.auto_restart:
                        LOG.WAR(f'Service {self} automatically restarting...')
                        time.sleep(60)
                        continue
                    LOG.WAR(f'Service {self} failed.')
                time.sleep(loop_delay)
            else:
                self.stop = False
        self.thread = CustomThread()
        self.args = None
        self.kwargs = None
        self.func = decorated
        self.service_name: str = service_name
        self.auto_restart: bool = auto_restart
        self.stop = False

    def __str__(self):
        return self.service_name

    def __repr__(self):
        return f'<Service {self.service_name}> at {hex(id(self))}'

    def start(self, *args, **kwargs):
        assert self.func
        assert not self.is_alive()
        self.args = args
        self.kwargs = kwargs
        self.thread = CustomThread(target=self.func, args=self.args, kwargs=self.kwargs, daemon=True)
        self.thread.start()
        LOG.INF(f'Service {self} started.')

    def stop(self, timeout=None):
        LOG.INF(f'Service {self} stopping...')
        self.stop = True
        self.thread.stop(timeout)
        LOG.INF(f'Service {self} stopped.')

    def is_alive(self):
        return self.thread.is_alive()