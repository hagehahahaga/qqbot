from abstract.bases.importer import abc, threading, enum
from enum import Enum, auto  # 用于状态管理


# 操作状态枚举（所有可中断IO操作的通用状态）
class OperationStatus(Enum):
    INITIALIZED = auto()  # 已初始化，未启动
    RUNNING = auto()      # 正在执行
    COMPLETED = auto()    # 正常完成
    INTERRUPTED = auto()  # 被中断
    FAILED = auto()       # 执行失败


# 抽象基类：可中断IO操作
class InterruptibleTask(metaclass=abc.ABCMeta):
    def __init__(self, session=None):
        """
        :type session: abstract.session.Session
        """
        self._status = OperationStatus.INITIALIZED  # 初始状态
        self._status_lock = threading.Lock()  # 状态更新的线程安全锁
        self._result_event = threading.Event()  # 结果就绪事件
        self.session = session

    @property
    def status(self) -> OperationStatus:
        """获取当前操作状态（线程安全）"""
        with self._status_lock:
            return self._status

    def _update_status(self, new_status: OperationStatus):
        """更新操作状态（线程安全，仅内部调用）"""
        with self._status_lock:
            self._status = new_status

    @abc.abstractmethod
    def start(self, *args, **kwargs):
        """
        启动IO操作（子类必须实现）
        调用后状态应变为 RUNNING
        """
        self._update_status(OperationStatus.RUNNING)
        if self.session:
            self.session.set_breakpoint(self)

    @abc.abstractmethod
    def stop(self):
        """
        中断IO操作（子类必须实现）
        调用后状态应变为 INTERRUPTED
        需确保操作能快速终止，不阻塞
        """
        self._update_status(OperationStatus.INTERRUPTED)
        self._result_event.set()  # 通知结果就绪

    @abc.abstractmethod
    def get_result(self, timeout=None):
        """
        获取操作结果（子类必须实现）
        - 堵塞等待操作完成（或超时）
        - 成功：返回结果（如response、文件内容等）
        - 中断：抛出 OperationInterruptedException
        - 失败：抛出 OperationErrorException
        - 超时：抛出 TimeoutError
        """
        # 等待结果就绪（由子类在操作结束时调用 self._result_event.set()）
        if not self._result_event.wait(timeout):
            raise TimeoutError("获取结果超时")

    def is_running(self) -> bool:
        """检查操作是否正在运行（通用实现，子类无需重写）"""
        return self.status == OperationStatus.RUNNING

    def run(self, *args, timeout=None, **kwargs):
        """
        运行操作（通用实现，子类无需重写）
        - 调用 start() 启动操作
        - 等待结果就绪
        """
        self.start(*args, **kwargs)
        return self.get_result(timeout=timeout)
