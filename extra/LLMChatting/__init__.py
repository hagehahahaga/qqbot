import pathlib

from abstract.bot import BOT

from .commands import *

BOT.register_help_text(pathlib.Path(__path__[0]) / 'help_text.json')