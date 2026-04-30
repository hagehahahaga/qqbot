from abstract.bases.importer import Iterable, inspect, functools
from typing import Optional

import abstract
from abstract.message import *
from abstract.bases.custom_thread import CustomThread
from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.message import MESSAGE_PART


class Command:
    def __init__(
            self,
            func,
            command_names: Iterable,
            type: int | dict[str, MESSAGE_PART | int] = 0,
            info=''
    ):
        def decorated(*args, **kwargs):
            session: abstract.session.Session = args[list(inspect.signature(func).parameters).index('session')]
            message: abstract.message.MESSAGE = args[list(inspect.signature(func).parameters).index('message')]

            thread = CustomThread(target=func, args=args, kwargs=kwargs)
            session.running_command = self
            session.running_thread = thread
            try:
                thread.start()
                thread.get_result()
            except SendFailure as error:
                LOG.WAR(error)
                message.reply_text(error.__str__())
            except CommandCancel as error:
                message.reply_text(error.__str__())
            except AssertionError as error:
                message.reply_text(f'检查不通过: {error}')
            except Exception as error:
                LOG.ERR(error)
                message.reply_text(f'错误: {error}. 哥我错啦——')
                raise
        self.func = decorated
        self.command_names = command_names
        self.type = type
        self.info = info

    def match(self, name):
        for command_name in self.command_names:
            if command_name == name:
                return True

        return False

    def __call__(self, *args, **kwargs):
        self.func(*args, **kwargs)


class CommandGroup(set):
    command_prefixes = ()

    def set_prefixes(self, prefixes: tuple[str]):
        self.command_prefixes = prefixes
        return self

    def add(self, command: Command):
        if not isinstance(command, Command):
            raise TypeError('CommandGroup only supports adding Command')
        super().add(command)

    def match(self: set[Command], command_name, need_prefix=True) -> Optional[Command | str]:
        """
        匹配命令名与命令组中的命令
        
        :param command_name: 要匹配的命令名
        :param need_prefix: 是否需要命令前缀匹配，默认为True
        
        :return: 匹配到的Command对象，或匹配失败时返回处理后的命令名字符串，
                当need_prefix为True且无匹配前缀时返回None
        """
        for command_prefix in self.command_prefixes:
            if command_name.startswith(command_prefix):
                command_name = command_name.removeprefix(command_prefix)
                break
        else:
            if need_prefix:
                return None  # 没有识别为指令

        for command in self:
            if command.match(command_name):
                return command  # 识别到存在的指令
        return command_name  # 不存在对应指令

    def register_command(self, command_name: str | Iterable, type: int | dict[str, MESSAGE_PART | int] = 0, info=''):
        """
        Register commands that runs them handling messages

        :param command_name:
        :param type:
        0 - no arg needed;
        1 - string arg needed;
        2 - message part arg needed;
        {
            'needed_type': MESSAGE_PART,
            'needed_num': int = 1
        } - assigned message parts arg needed:
        :return: decorated method
        """
        def decorator(func):
            self.add(Command(func, command_name, type, info))

            return func

        return decorator

    def __getitem__(self, item):
        return self.match(item)

COMMAND_GROUP = CommandGroup()


def ask_for_wait(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        wait_message: BaseMessage = args[0].reply_text('别急')
        try:
            return func(*args, **kwargs)
        finally:
            wait_message.delete()

    return decorated


def cost(cost: int):
    def decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            message = args[0]
            assert message.sender.get_points() >= cost, (
                f'韭菜盒子不足!'
                f'\n我早上本来应该吃 {cost} 个韭菜盒子, 饱饱的.'
                f'\n那我缺的这个这个营养这一块的, 谁给我补啊?'
            )

            result = func(*args, **kwargs)

            message.sender.add_points(-cost)
            message.reply_text(f'本次请求消耗 {cost} 个韭菜盒子, 贼jb好吃.')
            return result

        return decorated

    return decorator


def group_only(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        assert type(args[0]) is GroupMessage, '此指令仅在群聊中可用!'
        return func(*args, **kwargs)

    return decorated


def private_only(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        assert type(args[0]) is PrivateMessage, '此指令仅在私聊中可用'
        func(*args, **kwargs)

    return decorated


def authorize(min_level: str):
    level_list = ['member', 'admin', 'owner', 'operator']

    def decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            assert level_list.index(args[0].sender.role) >= level_list.index(min_level), \
                f'执行此指令最低需要{min_level}权限.'

            func(*args, **kwargs)

        return decorated

    return decorator
