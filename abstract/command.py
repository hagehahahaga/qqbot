from abstract.bases.importer import Iterable, threading, inspect

from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.message import MESSAGE_PART


class Command:
    def __init__(
            self,
            func,
            command_names: Iterable,
            type: int | dict[str, MESSAGE_PART | int] = 0,
            info='',
            cancelable=False
    ):
        def decorated(*args, **kwargs):
            message = args[list(inspect.signature(func).parameters).index('message')]
            try:
                func(*args, **kwargs)
            except SendFailure as error:
                LOG.WAR(error)
                message.reply_text(error.__str__())
            except (CommandCancel, OperationInterrupted) as error:
                LOG.WAR(error)
                message.reply_text(error.__str__())
            except AssertionError as error:
                LOG.WAR(error)
                message.reply_text(f'检查不通过: {error.__str__()}.')
            except Exception as error:
                LOG.ERR(error)
                message.reply_text(f'错误: {error}. 哥我错啦——')
                raise error
        self.func = decorated
        self.command_names = command_names
        self.type = type
        self.info = info
        self.cancelable = cancelable
        self._stop_event = threading.Event()

    def match(self, name):
        for command_name in self.command_names:
            if command_name == name:
                return True

        return False

    def __call__(self, *args, **kwargs):
        self.func(*args, **kwargs)


class CommandGroup(set):
    def add(self, command: Command):
        if not isinstance(command, Command):
            raise TypeError('CommandGroup only supports adding Command')
        super().add(command)

    def match(self: set[Command], command_name):
        for command in self:
            if command.match(command_name):
                return command

        raise KeyError('Not matched.')

    def __getitem__(self, item):
        return self.match(item)
