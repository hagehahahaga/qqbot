from abstract.bases.importer import time, datetime

from abstract.apis.table import *
from abstract.bases.exceptions import *
from abstract.message import *
from abstract.bases.log import LOG
from abstract.bot import BOT
from abstract.target import Group, User
from extra.weather_city import WEATHER_CITY_MANAGER


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


@BOT.register_service('weather_noticer', auto_restart=True)
def weather_noticer():
    # 获取当前时间
    now = datetime.datetime.now()

    # 计算今天的目标时间
    target_time = now.replace(hour=6, minute=30, second=0, microsecond=0)

    # 如果当前时间已过今天的目标时间，则设定为明天的目标时间
    if now > target_time:
        target_time += datetime.timedelta(days=1)

    # 计算需要等待的秒数
    wait_seconds = (target_time - now).total_seconds()

    # 等待到目标时间
    time.sleep(wait_seconds)

    # 执行任务
    for id, city in GROUP_OPTION_TABLE.get_all('where weather_notice = 1', attr="id, city"):
        id = int(id)
        try:
            if not city:
                GROUP_OPTION_TABLE.set('city', city, 'weather_notice', 0)
                try:
                    GroupMessage(
                        f'此群未设置默认天气城市, 已关闭天气提醒服务.',
                        Group(id)
                    ).send()
                except SendFailure as e:
                    LOG.WAR(e)
                continue

            try:
                city = WEATHER_CITY_MANAGER[city]
            except CityNotFound:
                GROUP_OPTION_TABLE.set('city', city, 'city', None)
                LOG.WAR(f'City {city} from group {id} not found, reset from group options.')
                try:
                    GroupMessage(
                        f'未能找到此群默认城市 {city}, 已重置天气选项.',
                        Group(id)
                    ).send()
                except SendFailure as e:
                    LOG.WAR(e)
                continue

            GroupMessage(
                [
                    TextMessage(city.get_weather_today_text()),
                    ImageMessage(city.get_weather_hourly())
                ],
                Group(id)
            ).send()
        except SendFailure as e:
            LOG.WAR(e)
        except Exception as e:
            LOG.ERR(e)
