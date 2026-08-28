import threading
from abc import ABC, abstractmethod
from typing import Callable, Literal

import tornado.web
from pydantic import IPvAnyAddress

from abstract.apis.ws_manager import WSManager
from abstract.bases.importer import json

from abstract.bases.log import *


class BaseReceiver(ABC):
    def __init__(self):
        self.callback: list[Callable[[dict,], None]] = []

    def register_callback(self, function: Callable[[dict,], None]) -> Callable[[dict,], None]:
        self.callback.append(function)
        return function
    
    @abstractmethod
    def start(self) -> None:
        ...


class WSMessageReceiver(BaseReceiver, WSManager):
    def __init__(self, host: IPvAnyAddress, port: int, token: str, **_):
        WSManager.__init__(self, f'ws://{host}:{port}/?access_token={token}')
        BaseReceiver.__init__(self)
    
    @WSManager._auto_reconnect
    def _receive_loop(self):
        LOG.INF('WS服务端已连接, 正在接受消息.')
        while True:
            data = self._receive()
            if data is None:
                continue
            
            for callback in self.callback:
                threading.Thread(target=callback, args=(data,)).start()
    
    def start(self):
        self._receive_loop()


class HttpMessageReceiver(BaseReceiver):
    class RootHandler(tornado.web.RequestHandler):
        def post(self):
            data = json.loads(self.request.body)
            for callback in self.application.settings['callbacks']:
                threading.Thread(
                    target=callback,
                    args=(data,)
                ).start()
            self.write(json.dumps({}))
    
    def __init__(self):
        super().__init__()
        self.app = tornado.web.Application(
            [
                ('/', self.RootHandler)
            ],
            callbacks=self.callback
        )
        for port in range(1024, 45192):
            try:
                self.app.listen(port)
            except:
                continue
            self.port = port
            break
        self.loop = tornado.ioloop.IOLoop.current()
    
    def start(self):
        LOG.INF(f'Receive server starting up at port {self.port}.')
        self.loop.start()


class MessageReceiver:
    def __new__(cls, mode: Literal['ws', 'http'], *args, **kwargs) -> BaseReceiver:
        match mode:
            case 'ws':
                return WSMessageReceiver(*args, **kwargs)
            case 'http':
                return HttpMessageReceiver()
            case others:
                raise ValueError(f'The mode {others} is not supported.')


LOG.INF('Initializing message receiver...')
MESSAGE_RECEIVER = MessageReceiver(**CONFIG.frame_server_config.model_dump())
LOG.INF(f'Message receiver loaded on mode {CONFIG.frame_server_config.mode}')
