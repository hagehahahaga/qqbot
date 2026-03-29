from abstract.bases.importer import time

from abstract.apis.table import *
from abstract.bases.exceptions import *
from abstract.message import *
from abstract.bot import BOT
from abstract.target import Group, User


@BOT.register_service('noticer', 1, auto_restart=True)
def noticer():
    for notice in NOTICE_SCHEDULE_TABLE.get_all(f'where time(time) = "{time.strftime("%H:%M:%S")}"'):
        target_id = int(notice[0])
        match notice[4]:
            case 'day':
                ...
            case 'week':
                if notice[2].weekday() > time.localtime().tm_wday:
                    time.sleep(1)
                    continue
            case _:
                if notice[2].date() > datetime.datetime.now().date():
                    continue
                NOTICE_SCHEDULE_TABLE.delete(
                    '(id, type, time)',
                    (target_id, notice[1], notice[2])
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
        except GroupNotJoined:
            NOTICE_SCHEDULE_TABLE.delete(
                f'(id, type, time)',
                (target_id, notice[1], notice[2])
            )


def get_wait_seconds(target_times: list[datetime.datetime]) -> float:
    """计算距离最近目标时间的等待秒数（通用时间处理逻辑）"""
    now = datetime.datetime.now()
    # 筛选未过期的目标时间，若均过期则取明天的同一时间
    valid_targets = [t if t > now else t + datetime.timedelta(days=1) for t in target_times]
    nearest_target = min(valid_targets)  # 取最近的目标时间
    return (nearest_target - now).total_seconds()
