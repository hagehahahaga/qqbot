import abstract
from abstract.bases.importer import queue, threading, time, inspect, local_time, datetime
from typing import Optional
from types import FrameType

from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.target import User
from abstract.message import MESSAGE, TextMessage, MESSAGE_PART, ReplyMessage


class Session:
    def __init__(self, manager):
        """

        :param manager:
        :type manager: SessionManager
        """
        self.manager = manager

        self.lock = threading.Lock()
        self.is_locked = False  # 添加这个属性来跟踪锁的状态
        self.pipe = queue.Queue()
        self.getting = False
        self.running_command: Optional[abstract.command.Command] = None
        self.running_thread: Optional[abstract.bases.custom_thread.CustomThread] = None
        threading.Thread(target=self.auto_free, daemon=True).start()

    def __enter__(self):
        self.lock.acquire()
        self.is_locked = True  # 锁被获取时设置为 True

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.is_locked = False  # 锁被释放时设置为 False
        self.lock.release()

    def pipe_put(self, message: MESSAGE):
        self.pipe.put(message)

    def pipe_get(self, message: MESSAGE, inform=True, timeout: Optional[int | float] = 30):
        stacks = inspect.stack()
        top_pipe_get_frame: FrameType = next(filter(lambda a: a.function == self.pipe_get.__name__, stacks[::-1])).frame
        try:
            get_time = top_pipe_get_frame.f_locals['get_time']
        except KeyError:
            get_time = local_time()
        if get_time + datetime.timedelta(seconds=timeout) < local_time():
            raise CommandCancel('未继续输入.')
        timeout = (local_time() + datetime.timedelta(seconds=timeout) - get_time).total_seconds()
        if inform:
            notice_message = message.reply_text(f'正在等待输入{timeout}秒...发送"cancel"以取消.')
        try:
            self.getting = True
            result: MESSAGE = self.pipe.get(timeout=timeout)
            if result.target != message.target:
                result.reply_text(f'你现在有进行中的输入请求, 请在对应会话中处理: {message.target}')
                result = self.pipe_get(message, inform=False, timeout=timeout)
        except queue.Empty:
            raise CommandCancel('未继续输入.')
        finally:
            self.getting = False
            if inform:
                notice_message.delete()
        try:
            args = result.get_parts_by_type(TextMessage)
            if args and args[0].to_args()[0] == 'cancel':
                raise CommandCancel('用户取消输入.')
        except IndexError:
            ...
        return result

    def pipe_get_by_type(self, message: MESSAGE, needed_type: type[MESSAGE_PART], num: int = 1) -> list[MESSAGE_PART]:
        output = message.get_parts_by_type(needed_type)
        if isinstance(message.messages[0], ReplyMessage):
            output.extend(message.messages[0].get_reply_message().get_parts_by_type(needed_type))

        notice_messages: set[MESSAGE] = set()
        try:
            while len(output) < num:
                notice_messages.add(
                    message.reply_text(
                        f'需要{num}个{needed_type.NAME}, 提供了{len(output)}个, 继续输入.'
                    )
                )

                message_got = self.pipe_get(message)
                if message_got and isinstance(message_got.messages[0], ReplyMessage):
                    output.extend(message_got.messages[0].get_reply_message().get_parts_by_type(needed_type))

                output.extend(message_got.get_parts_by_type(needed_type))
        finally:
            for notice_message in notice_messages:
                notice_message.delete()

        return output[:num]

    def handle(self, message: MESSAGE, command):
        from abstract.command import Command
        if isinstance(command, Command):
            message.reply_text('你现在还有进行中的命令.')
            return

        if command != 'cancel':
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
                if self.is_locked:
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

    def _new_session(self, user: int | str | User):
        if isinstance(user, User):
            user = user.id
        assert not self.get(user), 'The session has already existed!'
        session = Session(self)
        self[user] = session
        return session

    def get_session(self, user: int | str | User) -> Session:
        if isinstance(user, User):
            user = user.id
        if session := self.get(user):
            return session
        return self._new_session(user)


LOG.INF('Initializing session manager...')
SESSION_MANAGER = SessionManager()
LOG.INF('Session manager initialized successfully.')
