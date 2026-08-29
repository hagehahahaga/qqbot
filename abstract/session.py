import abstract
from abstract.bases.importer import queue, threading, time, SENTINEL
from typing import Optional, Callable

from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.bases.custom_thread import CustomThread
from abstract.target import User
from abstract.message import MESSAGE, TextMessage, MESSAGE_PART, ReplyMessage, GroupMessage


class Session:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_locked = False  # 添加这个属性来跟踪锁的状态
        self.acquire_event = threading.Event()
        self.pipe = queue.Queue()
        self.getting = False
        self.running_command: Optional[abstract.command.Command] = None
        self.running_thread: Optional[CustomThread] = None
        self.deadline: Optional[int | float] = None
        self.put_condition: Optional[Callable[[MESSAGE], bool]] = None

    def __enter__(self):
        self.lock.acquire()
        self.is_locked = True  # 锁被获取时设置为 True
        self.acquire_event.set()

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.acquire_event.clear()
        self.is_locked = False  # 锁被释放时设置为 False
        self.lock.release()

    @staticmethod
    def _lock_checker(func):
        def wrapper(self: Session, *args, **kwargs):
            assert self.is_locked, 'Can NOT access without with statement.'
            return func(self, *args, **kwargs)
        return wrapper

    def pipe_put(self, message: MESSAGE):
        """
        向会话管道投递消息，供正在阻塞的 pipe_get 取出处理.

        功能说明：
        - 若已设置 put_condition 且消息不满足该条件，则向管道投递 SessionTransfer 信号，
          通知持锁的 pipe_get 主动释放锁以让渡给更高优先级的交互，本函数返回 False.
        - 否则将真实消息投递进管道，返回 True.
        - put_condition 由 pipe_get(condition=...) 设置，用于过滤只接受特定类型的输入请求.
        - 若 put_condition 调用抛异常，记警告并当次放行真实消息（保留 condition 不清空），
          让 pipe_get 既有逻辑接管.

        :param message: 待投递的消息
        :type message: MESSAGE
        :return: 是否投递了真实消息（True 投递成功，False 因条件不满足转为让锁信号）
        :rtype: bool
        """
        if self.put_condition:
            try:
                cond_met = self.put_condition(message)
            except Exception as e:
                LOG.WAR(f'put_condition raised, fallback to pass-through: {e}')
            else:
                if not cond_met:
                    self.pipe.put(SessionTransfer())
                    return False
        self.pipe.put(message)
        return True

    @_lock_checker
    def pipe_get(
            self,
            message: MESSAGE,
            inform=True,
            timeout: Optional[int | float] = 30,
            condition: Optional[Callable[[MESSAGE], bool]] = SENTINEL
    ) -> MESSAGE:
        """
        从会话管道阻塞地取出一条由 pipe_put 投递的消息.

        功能说明：
        - 必须在 `with session:` 持锁上下文内调用（由 _lock_checker 强制）.
        - inform=True 时会发送"正在等待输入..."提示消息，取到消息后删除该提示.
        - timeout 为等待超时秒数：None 表示无限期等待；超时或队列空时抛 CommandCancel.
        - condition 用 SENTINEL 哨兵区分"未传参"与"显式传 None"：
          * 仅当 condition is not SENTINEL 时才更新 self.put_condition（传 None 即清空条件）；
          * 设定后 pipe_put 会据此决定投递真实消息还是 SessionTransfer 让锁信号.
        - 取到的消息若来自其它会话目标，会提示用户去对应会话处理并继续等待.
        - 若用户输入"cancel"，抛 CommandCancel 取消当前输入请求.
        - 取到 SessionTransfer 信号时向外抛出，由上层（如 game.runner）释放锁并等待重新获取.

        :param message: 触发本次输入请求的消息（用于回复提示与校验目标）
        :type message: MESSAGE
        :param inform: 是否发送"正在等待输入"提示，默认 True
        :type inform: bool
        :param timeout: 等待超时秒数，None 表示无限期，默认 30
        :type timeout: Optional[int | float]
        :param condition: 输入过滤函数，返回 True 才接受该消息；SENTINEL 表示不修改现有条件
        :type condition: Optional[Callable[[MESSAGE], bool]]
        :return: 取到的消息
        :rtype: MESSAGE
        :raises CommandCancel: 超时、队列为空或用户输入"cancel"时抛出
        :raises SessionTransfer: 收到让锁信号时抛出，由上层处理锁的让渡
        """
        if timeout is None:
            self.deadline = None
        else:
            self.deadline = time.time() + timeout

        if condition is not SENTINEL:
            self.put_condition = condition

        return self._pipe_get(message, inform)

    def _pipe_get(
            self,
            message: MESSAGE,
            inform=True
    ) -> MESSAGE:
        if self.deadline is not None:
            if self.deadline < time.time():
                raise CommandCancel('未继续输入.')
            timeout = self.deadline - time.time()
        else:
            timeout = None

        if inform:
            timeout_text = f'{int(timeout)}秒' if timeout is not None else '无限期'
            notice_message = message.reply_text(f'正在等待输入{timeout_text}...发送"cancel"以取消.')

        try:
            self.getting = True
            result: MESSAGE | SessionTransfer = self.pipe.get(timeout=timeout)
            if isinstance(result, SessionTransfer):
                raise result

            if result.target != message.target:
                if isinstance(message, GroupMessage):
                    assert message.target.has_member(message.sender)
                result.reply_text(f'你现在有进行中的输入请求, 请在对应会话中处理: {message.target}')
                result = self._pipe_get(message, inform=False)
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

    @_lock_checker
    def pipe_get_by_type(self, message: MESSAGE, needed_type: type[MESSAGE_PART], num: int = 1) -> list[MESSAGE_PART]:
        """
        收集指定数量的特定类型消息部件，不足时阻塞等待用户继续输入.

        功能说明：
        - 必须在 `with session:` 持锁上下文内调用（由 _lock_checker 强制）.
        - 初始 output 由当前 message 自身的 needed_type 部件构成；若 message 首部为
          ReplyMessage，还会从被回复的消息中提取同类型部件（支持"回复一条含图片的消息来补充图片"）.
        - 当 output 不足 num 个时进入循环：发送"需要N个X，提供了M个，继续输入"提示，
          调用 pipe_get 阻塞等待下一条消息；新消息若首部为回复消息，同样从其回复目标提取.
        - finally 块统一删除本轮所有提示消息.
        - 返回 output[:num]，即截断到恰好 num 个部件.
        - 内部依赖 pipe_get，故会透传其 CommandCancel（超时/取消）与 SessionTransfer（让锁）异常.

        :param message: 触发本次收集请求的消息
        :type message: MESSAGE
        :param needed_type: 需要收集的消息部件类型
        :type needed_type: type[MESSAGE_PART]
        :param num: 需要的部件数量，默认 1
        :type num: int
        :return: 收集到的消息部件列表，长度恰为 num
        :rtype: list[MESSAGE_PART]
        :raises CommandCancel: 等待输入超时或用户输入"cancel"时由 pipe_get 抛出
        :raises SessionTransfer: 收到让锁信号时由 pipe_get 抛出
        """
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

        if isinstance(command, str) and command != 'cancel':
            message.reply_text(f'{command}不是一个可识别的指令, 检查输入.')
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


class SessionManager(dict):
    def __init__(self):
        super().__init__()

    def get(self, key: int | str, default: None = None, /) -> Session | None:
        return super().get(key, default)

    def _new_session(self, user: int | str | User):
        if isinstance(user, User):
            user = user.id
        assert not self.get(user), 'The session has already existed!'
        session = Session()
        self[user] = session
        CustomThread(target=self.auto_free, args=(user, ), daemon=True).start()
        return session

    def get_session(self, user: int | str | User) -> Session:
        if isinstance(user, User):
            user = user.id
        if session := self.get(user):
            return session
        return self._new_session(user)

    def auto_free(self, id: int | str):
        while True:
            for i in range(30):
                time.sleep(1)
                if self[id].is_locked:
                    break
            else:
                self.pop(id)
                LOG.DEB(f'Session of {id} auto freed.')
                return


LOG.INF('Initializing session manager...')
SESSION_MANAGER = SessionManager()
LOG.INF('Session manager initialized successfully.')
