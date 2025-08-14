from abstract.bases.importer import threading, os, requests, socket
from abstract.bases.importer import select
from requests.adapters import HTTPAdapter
from  requests import RequestException
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.util import connection

from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.bases.interruptible_tasks.interruptible_task import InterruptibleTask, OperationStatus


current_socket = threading.local()


def _interruptible_new_conn(self):
    """替换 urllib3 的 _new_conn 方法，正确传递 address 参数"""
    try:
        # 构建正确的 (host, port) 元组（复用 urllib3 内部的 DNS 解析结果和端口）
        address = (self._dns_host, self.port)
        # 调用底层 create_connection，传递正确的 address 元组
        sock = connection.create_connection(
            address,  # 正确的 (host, port) 元组
            self.timeout,
            source_address=self.source_address,
            socket_options=self.socket_options,
        )
        # 存储 socket 到线程本地变量
        current_socket.sock = sock
        return sock
    except Exception as e:
        print(f"创建连接时出错: {e}")
        raise  # 保持原有错误处理逻辑


# 替换urllib3的默认连接创建函数
HTTPConnection._new_conn = _interruptible_new_conn
HTTPSConnection._new_conn = _interruptible_new_conn


class InterruptibleRequest(InterruptibleTask):
    def __init__(self, session):
        super().__init__(session)
        self._thread = None
        self._response = None
        self._exception = None

        # 跨平台中断通知机制：Windows 用套接字对，类 Unix 用管道
        if os.name == 'nt':  # Windows 系统
            # 创建本地套接字对（替代管道）
            self._interrupt_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._interrupt_server.bind(('127.0.0.1', 0))  # 绑定随机端口
            self._interrupt_server.listen(1)
            server_addr = self._interrupt_server.getsockname()

            self._interrupt_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._interrupt_client.connect(server_addr)
            self._interrupt_r, _ = self._interrupt_server.accept()  # 读端（socket对象）
            self._interrupt_w = self._interrupt_client  # 写端（socket对象）
        else:  # 类 Unix 系统（Linux/macOS）
            self._interrupt_r, self._interrupt_w = os.pipe()  # 管道（整数fd）

    def _release_resource(self):
        # 关闭 socket（若存在）
        if hasattr(current_socket, 'sock'):
            try:
                current_socket.sock.close()
            except Exception as e:
                LOG.WAR(f"关闭socket时出错: {e}")
            finally:
                del current_socket.sock

        # 关闭中断通知用的资源（区分套接字和管道）
        try:
            if os.name == 'nt':  # Windows 关闭套接字
                self._interrupt_r.close()
                self._interrupt_w.close()
                self._interrupt_server.close()
            else:  # 类 Unix 关闭管道
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

            # 等待工作线程退出（设置超时避免永久阻塞）
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)

            self._release_resource()  # 释放资源

        super().stop()  # 调用基类更新状态为INTERRUPTED

    def get_result(self, timeout=None):
        """获取请求结果（实现抽象方法）"""
        super().get_result(timeout)  # 基类的超时等待逻辑

        if self._exception:
            raise self._exception

        return self._response

    def _request_worker(self, url, method, **kwargs):
        session = None
        try:
            session = requests.Session()
            session.mount("http://", HTTPAdapter())
            session.mount("https://", HTTPAdapter())

            req = requests.Request(method, url,** kwargs).prepare()
            send_kwargs = {"stream": True, "timeout": 10}
            conn = session.send(req, **send_kwargs, verify=True)

            if not hasattr(current_socket, 'sock'):
                self._exception = RequestException("socket 捕获失败")
                self._update_status(OperationStatus.FAILED)
                return

            sock = current_socket.sock
            try:
                sock_fd = sock.fileno()  # socket的整数fd
                # 关键修改：根据系统类型获取中断描述符的整数fd
                if os.name == 'nt':
                    # Windows 下 _interrupt_r 是socket对象，需取其fd
                    interrupt_fd = self._interrupt_r.fileno()
                else:
                    # 类 Unix 下 _interrupt_r 是管道fd（直接使用）
                    interrupt_fd = self._interrupt_r
            except OSError:
                # 初始化时socket已关闭：若响应已获取，视为正常；否则异常
                if conn:  # 响应已拿到，socket关闭是正常的
                    self._response = conn
                    self._update_status(OperationStatus.COMPLETED)
                else:
                    self._exception = RequestException("socket 初始化失败")
                    self._update_status(OperationStatus.FAILED)
                return

            if sock_fd < 0 or interrupt_fd < 0:
                # 初始fd无效：同样先检查是否已有响应
                if conn:
                    self._response = conn
                    self._update_status(OperationStatus.COMPLETED)
                else:
                    self._exception = RequestException("初始文件描述符无效")
                    self._update_status(OperationStatus.FAILED)
                return

            read_fds = [sock_fd, interrupt_fd]

            while self.is_running():
                # 检查socket是否已关闭（正常关闭的核心判断）
                try:
                    current_fd = sock.fileno()
                    if current_fd != sock_fd:  # fd变化，说明socket已关闭并重建（极少发生）
                        raise OSError("socket 已重建")
                except OSError:
                    # socket已关闭：判断是否已有响应
                    if self._response:  # 响应已获取，正常结束
                        self._update_status(OperationStatus.COMPLETED)
                        break
                    else:  # 未获取响应就关闭，视为异常
                        self._exception = RequestException("socket 意外关闭（未接收响应）")
                        self._update_status(OperationStatus.FAILED)
                        break

                if interrupt_fd < 0:
                    # 管道关闭：若已有响应则正常结束，否则异常
                    if self._response:
                        self._update_status(OperationStatus.COMPLETED)
                        break
                    else:
                        self._exception = RequestException("中断管道意外关闭")
                        self._update_status(OperationStatus.FAILED)
                        break

                try:
                    # 再次验证 socket 有效性（避免竞态条件）
                    if sock.fileno() != sock_fd:
                        raise OSError("socket 已关闭或重建")
                except OSError:
                    # socket 已无效，处理逻辑
                    if self._response:
                        self._update_status(OperationStatus.COMPLETED)
                    else:
                        self._exception = RequestException("socket 已关闭（操作中断）")
                        self._update_status(OperationStatus.FAILED)
                    break

                # 执行select（带超时，避免永久阻塞）
                try:
                    ready_fds, _, _ = select.select(read_fds, [], [], 0.1)
                except ValueError as e:
                    # select失败：若已有响应则忽略，否则报错
                    if self._response:
                        self._update_status(OperationStatus.COMPLETED)
                        break
                    else:
                        self._exception = RequestException(f"select 失败：{str(e)}")
                        self._update_status(OperationStatus.FAILED)
                        break
                except OSError as e:
                    # 处理 Windows 非套接字操作错误
                    if hasattr(e, 'winerror') and e.winerror == 10038:
                        # 此时 socket 已无效，判断是否已有响应
                        if self._response:
                            self._update_status(OperationStatus.COMPLETED)
                        else:
                            self._exception = RequestException(f"套接字已关闭：{str(e)}")
                            self._update_status(OperationStatus.FAILED)
                        break
                    # 处理其他 select 错误
                    if self._response:
                        self._update_status(OperationStatus.COMPLETED)
                    else:
                        self._exception = RequestException(f"select 失败：{str(e)}")
                        self._update_status(OperationStatus.FAILED)
                    break

                if interrupt_fd in ready_fds:
                    os.read(interrupt_fd, 1)
                    break

                if sock_fd in ready_fds:
                    # 读取响应（标记响应已获取）
                    self._response = conn
                    self._update_status(OperationStatus.COMPLETED)
                    break

        except Exception as e:
            # 仅在未完成且非中断状态时视为错误
            if not self.status in (OperationStatus.INTERRUPTED, OperationStatus.COMPLETED):
                self._exception = RequestException(f"请求失败: {str(e)}")
                self._update_status(OperationStatus.FAILED)

        finally:
            if session:
                session.close()
            self._result_event.set()
