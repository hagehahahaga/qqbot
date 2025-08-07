from abstract.bases.importer import queue, threading, dispatch, time

from abstract.bases.exceptions import *
from abstract.bases.iterruptible_tasks.iterruptible_task import InterruptibleTask
from abstract.bases.log import LOG
from abstract.command import Command
from abstract.target import User
from abstract.message import MESSAGE, TextMessage, text_to_args


class Session:
    def __init__(self, pool):
        """

        :param pool:
        :type pool: SessionManager
        """
        self.lock = threading.Lock()
        self.pool = pool
        self.pipe = queue.Queue()
        self.getting = False
        self.break_point_set = threading.Event()  # 用于标记是否设置了断点
        self.command: Command = None
        self.break_point: InterruptibleTask = None
        threading.Thread(target=self.auto_free).start()

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

    def pipe_put(self, message: MESSAGE):
        self.pipe.put(message)

    def set_breakpoint(self, task: InterruptibleTask):
        self.break_point = task
        self.break_point_set.set()

    def pipe_get(self, message: MESSAGE):
        message.reply_text('正在等待输入...发送"cancel"以取消.')
        timeout = 30
        try:
            self.getting = True
            result: MESSAGE = self.pipe.get(timeout=timeout)
        except queue.Empty:
            raise AssertionError(f'{timeout}秒内未继续输入, 指令已取消')
        finally:
            self.getting = False
        args = result.get_parts_by_type(TextMessage)
        if args and text_to_args(args[0].text)[0] == 'cancel':
            raise CommandCancel('用户取消输入.')
        return result

    def handle(self, message: MESSAGE, command_name, is_command: bool):
        if command_name == 'cancel':
            if not self.command.cancelable:
                message.reply_text('该指令还未实现取消.')
                return

            message.reply_text('尝试取消中...')
            if self.break_point_set.wait():
                self.break_point.stop()
            LOG.INF(f'{message.sender} canceled {next(iter(self.command.command_names))}')
            return
        if not (is_command and command_name):
            return
        message.reply_text('你现在还有进行中的任务.')

    def auto_free(self):
        while True:
            for i in range(30):
                time.sleep(1)
                if self.lock.locked():
                    break
            else:
                for key, value in list(self.pool.pool.items()):
                    if value == self:
                        del self.pool.pool[key]
                        break


class SessionManager:
    def __init__(self):
        self.pool = {}

    def new_session(self, id: int):
        assert not self.pool.get(id), 'The session has already existed!'
        session = Session(self)
        self.pool[id] = session
        return session

    @dispatch
    def get_session(self, id: int) -> Session:
        if session := self.pool.get(id):
            return session
        return self.new_session(id)

    @dispatch
    def get_session(self, user: User) -> Session:
        return self.get_session(user.id)


LOG.INF('Initializing session manager...')
SESSIONMANAGER = SessionManager()
LOG.INF('Session manager initialized successfully.')
