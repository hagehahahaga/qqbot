import json
import queue
import threading
import time
import uuid
from typing import Optional

from websockets.sync.client import ClientConnection, connect
from websockets import ConnectionClosed

from abstract.bases.log import LOG


class WSManager:
    def __init__(self, url: str):
        self._url = url
        self._con: ClientConnection = self._connect()
        self.action_recv_map: dict[str, queue.Queue] = {}
        self.lock = threading.Lock()

    @staticmethod
    def _auto_reconnect(func):
        def wrapper(self: WSManager, *args, **kwargs):
            while True:
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    match e:
                        case ConnectionClosed():
                            LOG.WAR('WS服务端已断开, 正在重连.')
                        case TimeoutError():
                            LOG.WAR('WS服务端连接超时, 正在重连.')
                        case _:
                            raise
                    time.sleep(5)
                    self._connect()

        return wrapper

    @_auto_reconnect
    def _connect(self):
        self._con = connect(
            self._url,
            open_timeout=None
        ).__enter__()
        return self._con
    
    def _receive(self) -> Optional[dict]:
        data = json.loads(self._con.recv(timeout=35))
        
        try:
            self.action_recv_map[data['echo']].put(data)
            return None
        except KeyError:
            pass
        
        return data
    
    @_auto_reconnect
    def _receive_loop(self):
        LOG.INF('WS服务端已连接, 正在接收回调.')
        while True:
            self._receive()
    
    @_auto_reconnect
    def send(self, action: str, params: Optional[dict[str, str | float| dict | list]] = None, *, echo: Optional[str] = None) -> dict:
        if params is None:
            params = {}
        if echo is None:
            echo = str(uuid.uuid7())
        pipe = queue.Queue()
        
        try:
            self.action_recv_map[echo] = pipe
            with self.lock:
                self._con.send(
                    json.dumps(
                        {
                            'action': action, 'params': params, 'echo': echo
                        }
                    )
                )
            return pipe.get()
        finally:
            pipe.shutdown(True)
            del self.action_recv_map[echo]
