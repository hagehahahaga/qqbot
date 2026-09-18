import getopt
import threading
from functools import cached_property
from typing import Callable

from pydantic import BaseModel

from abstract.bases.log import LOG


class Option(BaseModel):
    short_opts: str
    long_opts: list[str]


class OptionHandler:
    def __init__(self):
        self.registered_options: dict[str, Callable[[str,], None]] = {}

    def register(self, opt: str):
        def decorator[T: Callable[[str,], None]](func: T) -> T:
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    LOG.WAR(f'Exception occurred in registered option handler {opt} - {func}: {e}')

            self.registered_options[opt] = wrapper

            return func

        return decorator

    @cached_property
    def options(self) -> Option:
        result = Option(short_opts='', long_opts=[])
        for opt in self.registered_options.keys():
            assert opt.startswith('-'), f'Illegal option registration {opt}.'
            opt = opt[1:]
            if opt.startswith('-'):
                result.long_opts.append(opt.lstrip('-'))
                continue

            result.short_opts += opt

        return result


    def handle(self, opts: list[str]):
        result = getopt.gnu_getopt(opts, self.options.short_opts, self.options.long_opts)
        for opt, value in result[0]:
            threading.Thread(target=self.registered_options[opt], args=(value, )).start()


OPTION_HANDLER = OptionHandler()
