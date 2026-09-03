import pathlib

from abstract.bot import BOT

from .register import *
from .commands import *


User.init_tables.append(STOCK_TABLE)

BOT.register_help_text(pathlib.Path(__path__[0]) / 'help_text.json')