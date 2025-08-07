from abstract.bases.importer import threading, time, os, requests, urllib3
from abstract.bases.importer import select
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection
from urllib3.util import connection

from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.bases.iterruptible_tasks.iterruptible_task import InterruptibleTask, OperationStatus


current_socket = threading.local()


def _interruptible_socket_create_connection(address, *args, **kwargs):
    """替换urllib3的socket创建函数，捕获socket"""
    sock = connection.create_connection(address, *args, **kwargs)
    current_socket.sock = sock  # 存储到线程本地变量
    return sock


# 替换urllib3的默认连接创建函数
HTTPConnection._create_connection = _interruptible_socket_create_connection


class InterruptibleRequest(InterruptibleTask):
    def __init__(self, session):
        super().__init__(session)
        self._thread = None
        self._response = None  # 存储成功响应
        self._exception = None  # 存储异常
        self._interrupt_r, self._interrupt_w = os.pipe()  # 中断通知管道

    def _release_resource(self):
        """释放底层资源（实现抽象基类隐含的资源释放逻辑）"""
        # 关闭捕获的socket（若存在）
        if hasattr(current_socket, 'sock'):
            try:
                current_socket.sock.close()
            except Exception as e:
                LOG.WAR(f"关闭socket时出错: {e}")
            finally:
                del current_socket.sock  # 清除引用

        # 关闭管道（避免资源泄露）
        try:
            os.close(self._interrupt_r)
            os.close(self._interrupt_w)
        except OSError:
            pass

    def start(self, url, method="GET", **kwargs):
        """启动网络请求（实现抽象方法）"""
        super().start()  # 调用基类更新状态为RUNNING

        # 启动工作线程执行请求
        self._thread = threading.Thread(
            target=self._request_worker,
            args=(url, method),
            kwargs=kwargs
        )
        self._thread.start()

    def stop(self):
        """中断请求（实现抽象方法）"""
        if self.is_running():
            # 向管道写入数据，触发select返回
            os.write(self._interrupt_w, b'x')
            self._exception = OperationInterrupted("请求被主动中断")
            self._release_resource()  # 释放资源

        super().stop()  # 调用基类更新状态为INTERRUPTED

    def get_result(self, timeout=None):
        """获取请求结果（实现抽象方法）"""
        super().get_result(timeout)  # 基类的超时等待逻辑

        if self._exception:
            raise self._exception

        return self._response

    def _request_worker(self, url, method, **kwargs):
        """请求工作线程逻辑"""
        session = None
        try:
            session = requests.Session()
            session.mount("http://", HTTPAdapter())
            session.mount("https://", HTTPAdapter())

            # 准备请求
            req = requests.Request(method, url,** kwargs).prepare()
            send_kwargs = {"stream": True, "timeout": None}
            conn = session.send(req, **send_kwargs, verify=False)

            # 获取当前请求的socket（通过钩子函数存储）
            sock = current_socket.sock
            read_fds = [sock, self._interrupt_r]

            # 用select监听socket和中断管道
            while self.is_running():
                ready_fds, _, _ = select.select(read_fds, [], [])

                if self._interrupt_r in ready_fds:
                    # 收到中断信号（已在stop()中处理，此处仅退出循环）
                    os.read(self._interrupt_r, 1)
                    break

                if sock in ready_fds:
                    # 读取响应数据（此处简化为直接保存响应对象）
                    self._response = conn
                    self._update_status(OperationStatus.COMPLETED)
                    break

        except Exception as e:
            if not self.status == OperationStatus.INTERRUPTED:
                # 非中断导致的错误
                self._exception = e
                self._update_status(OperationStatus.FAILED)

        finally:
            if session:
                session.close()
            self._result_event.set()  # 通知结果就绪
