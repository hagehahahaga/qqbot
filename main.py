import threading
import time

from abstract.bases.importer import getopt, sys, last_commit, requests

from abstract.apis.frame_server import FRAME_SERVER
from abstract.bot import BOT
from abstract.bases.exceptions import *
from abstract.bases.log import LOG
from abstract.message import GroupMessage
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
                    '最近一次提交:\n'
                    f'   哈希: {last_commit.hexsha}\n'
                    f'   作者: {last_commit.author.name}\n'
                    f'   时间: {last_commit.committed_datetime}\n'
                    '   信息: \n'
                    f'{last_commit.message.strip()}',
                    Group(group_id)
                ).send()
            except SendFailure as error:
                LOG.WAR(error)


if __name__ == '__main__':
    threading.Thread(target=main).start()
    FRAME_CLIENT.start()
