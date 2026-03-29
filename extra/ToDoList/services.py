import datetime, time

from abstract.bases.exceptions import PrivateChatFailed, SendFailure
from abstract.bases.log import LOG
from abstract.apis.table import USER_TABLE
from abstract.message import PrivateMessage
from abstract.target import User
from abstract.bot import BOT
from services import get_wait_seconds

from .tables import TODOLIST_TABLE


@BOT.register_service('todo_noticer', 0, auto_restart=True)
def todo_noticer():
    now = datetime.datetime.now()
    target_times = [
        now.replace(hour=9, minute=0, second=0, microsecond=0),
        now.replace(hour=14, minute=00, second=0, microsecond=0),
        now.replace(hour=20, minute=00, second=0, microsecond=0)
    ]

    # 等待到目标时间
    wait_seconds = get_wait_seconds(target_times)
    time.sleep(wait_seconds)

    with TODOLIST_TABLE:
        TODOLIST_TABLE.cursor.execute(
            'select qq_users.id, group_concat(todo_list.do separator \',\') '
            'from qq_users '
            'join todo_list on qq_users.id = todo_list.user_id '
            'where qq_users.todo_notice = 1 '
            '   and todo_list.finished = 0 '
            'group by qq_users.id '
        )
        result = TODOLIST_TABLE.cursor.fetchall()

    for id, does in result:
        user = User(int(id))
        try:
            PrivateMessage(
                '你设定的以下待办还未完成:\n' + '\n'.join(does.split(',')),
                user
            ).send()
        except PrivateChatFailed:
            USER_TABLE.set('id', id, 'todo_notice', 0)
            LOG.WAR(f'Send to {user} failed.')

        except SendFailure as e:
            LOG.WAR(e)
        except Exception as e:
            LOG.ERR(e)
