import pathlib
import os
import git

from abstract.apis.frame_server import ONEBOT_SERVER
from abstract.bases.exceptions import SendFailure
from abstract.bases.log import LOG
from abstract.bot import BOT
from abstract.message import GroupMessage, TextImagePart, NodePart, BOT_USER, MESSAGE_PART, TextPart
from abstract.option_handler import OPTION_HANDLER
from abstract.target import Group


@OPTION_HANDLER.register('-p')
@OPTION_HANDLER.register('--post')
def post(_: str):
    REPO = git.Repo(os.getcwd())
    LAST_COMMIT_FILE = pathlib.Path(__file__).parent / 'last_commit'
    last_hexsha = REPO.head.commit.hexsha

    if not LAST_COMMIT_FILE.exists():
        LAST_COMMIT_FILE.write_text(last_hexsha)

    LAST_COMMIT = LAST_COMMIT_FILE.read_text()

    latest_commits = []
    for commit in REPO.iter_commits('master'):
        if commit.hexsha == LAST_COMMIT:
            break

        latest_commits.append(commit)

    message = []
    for commit in latest_commits[::-1]:
        message.append(
            NodePart(
                sender=BOT_USER, content=[
                    TextImagePart(
                        f'{commit.committed_datetime} 的提交:\n'
                        f'    哈希: {commit.hexsha}\n'
                        f'    作者: {commit.author.name}\n'
                        f'    信息: \n'
                        f'{commit.message.strip()}'
                    )
                ]
            )
        )

    messages: list[list[MESSAGE_PART]] = [[TextPart('机器人已重启' + BOT.VERSION)]]
    if message:
        messages[0][0].text += '\n以下是最近几次提交:'
        messages.append(message)

    for group_id in map(
            lambda a: a['group_id'], ONEBOT_SERVER.get_group_list()
    ):
        try:
            for message in messages:
                GroupMessage(
                    message, Group(group_id)
                ).send()
        except SendFailure as error:
            LOG.WAR(error)

    LAST_COMMIT_FILE.write_text(last_hexsha)
