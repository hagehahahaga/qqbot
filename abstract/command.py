from typing import Optional

from abstract.bases.importer import Iterable, inspect

import abstract
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
                message.reply_text(f'检查不通过: {error.__str__()}.')
            except Exception as error:
                LOG.ERR(error)
                message.reply_text(f'错误: {error}. 哥我错啦——')
                raise error
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
                return None

        for command in self:
            if command.match(command_name):
                return command
        return command_name

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
