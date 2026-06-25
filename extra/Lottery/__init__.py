from abstract.bot import BOT

from .commands import *

BOT.register_help_text(pathlib.Path(__file__.parent) / 'help_text.json')