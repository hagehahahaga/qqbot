from abstract.bases.importer import time, datetime

from abstract.apis.table import NOTICE_SCHEDULE_TABLE
from abstract.bot import BOT
from abstract.message import GroupMessage, PrivateMessage
from abstract.target import Group, User


@BOT.register_service('noticer', auto_restart=True)
def noticer():
    for notice in NOTICE_SCHEDULE_TABLE.get_all(f'where time(time) = "{time.strftime("%H:%M:%S")}"'):
        target_id = int(notice[0])
        match notice[4]:
            case 'day':
                ...
            case 'week':
                if notice[2].weekday() != time.localtime().tm_wday:
                    time.sleep(1)
                    continue
            case _:
                if notice[2].date() != datetime.datetime.now().date():
                    continue
                NOTICE_SCHEDULE_TABLE.delete(
                    f'(id, type, time)',
                    (target_id, notice[1], notice[2].strftime('%Y-%m-%d %H:%M:%S'))
                )

        try:
            match notice[1]:
                case 'group':
                    GroupMessage(
                        notice[3],
                        Group(target_id)
                    ).send()
                case 'private':
                    PrivateMessage(
                        notice[3],
                        User(target_id)
                    ).send()
        except TypeError:
            NOTICE_SCHEDULE_TABLE.delete(
                f'(id, type, time)',
                (target_id, notice[1], notice[2].strftime('%Y-%m-%d %H:%M:%S'))
            )

    time.sleep(1)
