import os
import pathlib

assert (pathlib.Path(os.getcwd()) / 'main.py').exists(), 'Please run in project root directory.'


from abstract.bases.importer import sys, threading

from abstract.bot import BOT
from abstract.bases.log import LOG
from abstract.option_handler import OPTION_HANDLER
from abstract.apis.receiver import MESSAGE_RECEIVER


import commands
LOG.INF('Commands registered successfully.')
import services
LOG.INF('Services registered successfully.')
import games
LOG.INF('Games registered successfully.')
import triggers
LOG.INF('Triggers registered successfully.')
BOT.register_help_text('help_text.json')
from extra import *
LOG.INF('Extras registered successfully.')


def main():
    OPTION_HANDLER.handle(sys.argv[1:])


if __name__ == '__main__':
    threading.Thread(target=main).start()
    MESSAGE_RECEIVER.start()
