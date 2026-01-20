import threading
import time

from abstract.bases.importer import getopt, sys, requests

from abstract.apis.frame_server import FRAME_SERVER
from abstract.bases.text2img import text2img
from abstract.bot import BOT
from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.message import GroupMessage, ImageMessage
from abstract.target import Group
from web import FRAME_CLIENT


import commands
LOG.INF('Commands registered successfully.')
import services
LOG.INF('Services registered successfully.')
import games
LOG.INF('Games registered successfully.')
import triggers
LOG.INF('Triggers registered successfully.')


def main():
    while True:
        try:
            login_info = FRAME_SERVER.get_login_info()
            assert login_info['user_id'] == BOT.id
        except (requests.ConnectionError, KeyError):
            time.sleep(1)
            continue
        break

    opt = dict(getopt.getopt(sys.argv[1:], 'p', ['post'])[0])
    if '-p' in opt or '--post' in opt:
        for group_id in map(
                lambda a: a['group_id'],
                FRAME_SERVER.get_group_list()
        ):
            try:
                GroupMessage(
                    ImageMessage(
                        text2img(
                            BOT.VERSION
                        )
                    ),
                    Group(group_id)
                ).send()
            except SendFailure as error:
                LOG.WAR(error)


if __name__ == '__main__':
    threading.Thread(target=main).start()
    FRAME_CLIENT.start()
