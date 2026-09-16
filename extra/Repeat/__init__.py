import pathlib

from .triggers import *
from .register import *


BOT.register_help_text(pathlib.Path(__path__[0]) / 'help_text.json')
