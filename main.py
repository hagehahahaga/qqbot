from abstract.bases.importer import getopt, sys
from abstract.bases.custom_thread import CustomThread

from abstract.apis.frame_server import ONEBOT_SERVER
from abstract.bot import BOT
from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.message import GroupMessage, TextImageMessage
from abstract.target import Group
from abstract.apis.receiver import MESSAGE_RECEIVER


import commands
LOG.INF('Commands registered successfully.')
import services
LOG.INF('Services registered successfully.')
import games
LOG.INF('Games registered successfully.')
import triggers
LOG.INF('Triggers registered successfully.')
from extra import *
LOG.INF('Extras registered successfully.')

BOT.register_help_text('help_text.json')


def main():
    opt = dict(getopt.getopt(sys.argv[1:], 'p', ['post'])[0])
    if '-p' in opt or '--post' in opt:
        for group_id in map(
                lambda a: a['group_id'],
                ONEBOT_SERVER.get_group_list()
        ):
            try:
                GroupMessage(
                    TextImageMessage(
                        '机器人已重启' +
                        BOT.VERSION
                    ),
                    Group(group_id)
                ).send()
            except SendFailure as error:
                LOG.WAR(error)


if __name__ == '__main__':
    CustomThread(target=main).start()
    MESSAGE_RECEIVER.start()
