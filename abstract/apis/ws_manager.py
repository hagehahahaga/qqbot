import json
import queue
import threading
import time
import uuid
from typing import Optional

from websockets.sync.client import ClientConnection, connect
from websockets import ConnectionClosed

from abstract.bases.exceptions import SendTimeout
from abstract.bases.log import LOG


class _RequestPipe(queue.Queue):
    """等待单个请求响应的队列, 记录接口名以便断线时构造带上下文的异常."""

    def __init__(self, action: str):
        super().__init__()
        self.action = action


class WSManager:
    RESPONSE_TIMEOUT = 300  # 单次请求等待响应的最长秒数, 超时后判定该请求已丢失

    def __init__(self, url: str):
        self._url = url
        self.action_recv_map: dict[str, _RequestPipe] = {}
        self.lock = threading.Lock()
        self._con: ClientConnection = self._connect()

    @staticmethod
    def _auto_reconnect(func):
        def wrapper(self: WSManager, *args, **kwargs):
            while True:
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    match e:
                        case ConnectionClosed():
                            LOG.WAR(f'WS服务端已断开, 正在重连. {e}')
                        case TimeoutError(), ConnectionRefusedError():
                            LOG.WAR('WS服务端连接超时, 正在重连.')
                        case _:
                            raise
                    time.sleep(5)
                    self._connect()

        return wrapper

    @_auto_reconnect
    def _connect(self):
        con = connect(
            self._url,
            open_timeout=None
        ).__enter__()
        with self.lock:
            self._con = con
            # 旧连接上在途的响应已不可能送达, 直接给其等待方放入异常, 而不是干等到超时
            for pipe in list(self.action_recv_map.values()):
                try:
                    pipe.put(SendTimeout(pipe.action))
                except queue.ShutDown:
                    pass
        return con
    
    def _receive(self) -> Optional[dict]:
        try:
            data = json.loads(self._con.recv(timeout=35))
        except TimeoutError:
            # 空闲超时: 连接本身仍然正常, 只是这段时间没有收到数据, 不能当作断线处理
            return None
        
        if 'echo' in data:
            try:
                self.action_recv_map[data['echo']].put(data)
            except (KeyError, queue.ShutDown):
                # 没有等待方(已超时放弃)的迟到响应, 直接丢弃
                pass
            return None
        
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
        pipe = _RequestPipe(action)
        
        try:
            with self.lock:
                self.action_recv_map[echo] = pipe
                self._con.send(
                    json.dumps(
                        {
                            'action': action, 'params': params, 'echo': echo
                        }
                    )
                )
            data = pipe.get(timeout=self.RESPONSE_TIMEOUT)
            if isinstance(data, BaseException):
                raise data
            return data
        except queue.Empty:
            # 不能无限等待响应: 响应一旦丢失, 调用线程会静默卡死, 且不会产生任何异常或日志
            raise SendTimeout(action)
        finally:
            pipe.shutdown(True)
            del self.action_recv_map[echo]
