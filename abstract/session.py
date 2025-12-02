import abstract
from abstract.bases.importer import queue, threading, dispatch, time
from typing import Optional

from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.target import User
from abstract.message import MESSAGE, TextMessage, text_to_args


class Session:
    def __init__(self, manager):
        """

        :param manager:
        :type manager: SessionManager
        """
        self.manager = manager

        self.lock = threading.Lock()
        self.pipe = queue.Queue()
        self.getting = False
        self.running_command: Optional[abstract.command.Command] = None
        self.running_thread: Optional[abstract.bases.custom_thread.CustomThread] = None
        threading.Thread(target=self.auto_free, daemon=True).start()

    def __enter__(self):
        self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()

    def pipe_put(self, message: MESSAGE):
        self.pipe.put(message)

    def pipe_get(self, message: MESSAGE):
        message.reply_text('正在等待输入...发送"cancel"以取消.')
        timeout = 30
        try:
            self.getting = True
            result: MESSAGE = self.pipe.get(timeout=timeout)
        except queue.Empty:
            raise CommandCancel(f'{timeout}秒内未继续输入.')
        finally:
            self.getting = False
        try:
            args = result.get_parts_by_type(TextMessage)
            if args and text_to_args(args[0].text)[0] == 'cancel':
                raise CommandCancel('用户取消输入.')
        except IndexError:
            ...
        return result

    def handle(self, message: MESSAGE, command_name, is_command: bool):
        if command_name != 'cancel':
            if not (is_command and command_name):
                return
            message.reply_text('你现在还有进行中的命令.')
            return

        if not self.running_thread.is_alive():
            message.reply_text('当前没有进行中的命令.')
            return

        wait_message = message.reply_text('正在取消当前命令...')
        try:
            self.running_thread.stop(timeout=None)
        finally:
            wait_message.delete()
        if self.running_thread.status != 'CANCELLED':
            message.reply_text('命令执行完成, 取消失败.')

    def auto_free(self):
        while True:
            for i in range(30):
                time.sleep(1)
                if self.lock.locked():
                    break
            else:
                for key, value in list(self.manager.items()):
                    if value is self:
                        self.manager.pop(key)
                        LOG.DEB(f'Session of {key} auto freed.')
                        return


class SessionManager(dict):
    def __init__(self):
        super().__init__()

    def new_session(self, id: int):
        assert not self.get(id), 'The session has already existed!'
        session = Session(self)
        self[id] = session
        return session

    @dispatch
    def get_session(self, id: int) -> Session:
        if session := self.get(id):
            return session
        return self.new_session(id)

    @dispatch
    def get_session(self, user: User) -> Session:
        return self.get_session(user.id)


LOG.INF('Initializing session manager...')
SESSIONMANAGER = SessionManager()
LOG.INF('Session manager initialized successfully.')
