import datetime, time
from typing import Callable, Type

from abstract.bases.importer import at_midnight
from services import get_wait_seconds

from abstract.apis.table import GROUP_OPTION_TABLE
from abstract.message import GroupMessage, ImageMessage, TextMessage
from abstract.target import Group
from abstract.bases.exceptions import SendFailure, GroupNotJoined
from abstract.bases.log import LOG
from abstract.bot import BOT

from .weather_city import WEATHER_CITY_MANAGER, WeatherCity
from .exceptions import CityNotFound


def _execute_weather_task(
        weather_getter: Callable,  # 获取天气数据的方法（差异化逻辑）
        message_cls: Type,  # 消息类型（ImageMessage/TextMessage，差异化逻辑）
        *args, **kwargs
):
    """执行天气提醒任务的通用逻辑（处理群组、城市验证、消息发送）"""
    for city in WEATHER_CITY_MANAGER.values():
        city.flush_cache(weather_getter)

    case = 'where weather_notice = 1'
    if at_midnight():
        case += ' and night_disturb = 1'
    for id, city in GROUP_OPTION_TABLE.get_all(case, attr="id, city"):
        group_id = int(id)
        try:
            # 处理未设置城市的情况
            if not city:
                GROUP_OPTION_TABLE.set('id', group_id, 'weather_notice', 0)
                try:
                    GroupMessage(
                        f'此群未设置默认天气城市, 已关闭天气提醒服务.',
                        Group(group_id)
                    ).send()
                except SendFailure as e:
                    LOG.WAR(e)
                continue

            # 验证城市是否存在
            try:
                city_obj = WEATHER_CITY_MANAGER[city]
            except CityNotFound:
                GROUP_OPTION_TABLE.set('id', group_id, 'weather_notice', 0)
                GROUP_OPTION_TABLE.set('id', group_id, 'city', None)
                LOG.WAR(f'City {city} from group {group_id} not found, reset from group options.')
                try:
                    GroupMessage(
                        f'未能找到此群默认城市 {city}, 已重置天气选项.',
                        Group(group_id)
                    ).send()
                except SendFailure as e:
                    LOG.WAR(e)
                continue

            # 发送对应类型的天气消息（差异化逻辑通过参数传入）
            result = weather_getter(city_obj, *args, **kwargs)
            if result is None:
                continue
            GroupMessage(
                message_cls(result),
                Group(group_id)
            ).send()

        except GroupNotJoined:
            GROUP_OPTION_TABLE.set('id', group_id, 'weather_notice', 0)
            LOG.WAR(f'Group {group_id} not joined, option weather_notice set to 0.')

        except SendFailure as e:
            LOG.WAR(e)
        except Exception as e:
            LOG.ERR(e)


@BOT.register_service('weather_predictor_hourly', 0, auto_restart=True)
def weather_predictor_hourly():
    # 每小时任务的差异化参数：目标时间、天气获取方法、消息类型
    now = datetime.datetime.now()
    target_times = [
        now.replace(hour=6, minute=30, second=0, microsecond=0),
        now.replace(hour=23, minute=0, second=0, microsecond=0),
    ]

    # 等待到目标时间
    wait_seconds = get_wait_seconds(target_times)
    time.sleep(wait_seconds)

    # 执行任务（传入 hourly 特有的逻辑，先清除缓存）
    _execute_weather_task(
        weather_getter=WeatherCity.get_weather_hourly,
        message_cls=ImageMessage
    )


@BOT.register_service('weather_predictor_daily', 0, auto_restart=True)
def weather_predictor_daily():
    # 每日任务的差异化参数：目标时间、天气获取方法、消息类型
    now = datetime.datetime.now()
    target_times = [
        now.replace(hour=23, minute=0, second=0, microsecond=0)
    ]

    # 等待到目标时间
    wait_seconds = get_wait_seconds(target_times)
    time.sleep(wait_seconds)

    # 执行任务（传入 daily 特有的逻辑，先清除缓存）
    _execute_weather_task(
        weather_getter=WeatherCity.get_weather_day_text,
        message_cls=TextMessage,
        delay=1
    )


@BOT.register_service('weather_today', 0, auto_restart=True)
def weather_today():
    # 每日任务的差异化参数：目标时间、天气获取方法、消息类型
    now = datetime.datetime.now()
    target_times = [
        now.replace(hour=6, minute=30, second=0, microsecond=0)
    ]

    # 等待到目标时间
    wait_seconds = get_wait_seconds(target_times)
    time.sleep(wait_seconds)

    # 执行任务（传入 daily 特有的逻辑，先清除缓存）
    _execute_weather_task(
        weather_getter=WeatherCity.get_weather_day_text,
        message_cls=TextMessage
    )


@BOT.register_service('weather_predictor_weekly', 0, auto_restart=True)
def weather_predictor_weekly():
    """每周日12点执行一次，发送7天天气预报图表（修复负等待时间问题）"""
    now = datetime.datetime.now()

    # 计算下一个周日23:00:00
    days_until_sunday = (6 - now.weekday()) % 7  # 0=今天是周日，1=明天是周日，...，6=下周六
    next_sunday = now + datetime.timedelta(days=days_until_sunday)
    target_time = next_sunday.replace(hour=12, minute=0, second=0, microsecond=0)

    # 关键修复：如果目标时间已过期（如周日23点后执行），则延后一周
    if target_time <= now:
        target_time += datetime.timedelta(days=7)

    # 等待到目标时间（此时wait_seconds一定非负）
    wait_seconds = (target_time - now).total_seconds()
    time.sleep(wait_seconds)

    # 执行任务（复用现有逻辑，先清除缓存）
    _execute_weather_task(
        weather_getter=WeatherCity.get_weather_daily,
        message_cls=ImageMessage
    )


@BOT.register_service('weather_predictor_minutely', 0, auto_restart=True)
def weather_predictor_minutely():
    """每五分钟执行一次，发送分钟级降水变化预报"""
    now = datetime.datetime.now()

    # 计算当前时间的总分钟数
    total_minutes = now.hour * 60 + now.minute

    # 计算下一个5分钟的总分钟数
    next_total_minutes = ((total_minutes // 5) + 1) * 5

    # 计算需要等待的分钟数
    wait_minutes = next_total_minutes - total_minutes

    # 计算目标时间，使用timedelta自动处理跨天情况
    target_time = now + datetime.timedelta(minutes=wait_minutes)
    target_time = target_time.replace(second=0, microsecond=0)

    # 等待到目标时间
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        time.sleep(wait_seconds)

    # 执行任务（获取分钟级降水变化预报）
    _execute_weather_task(
        weather_getter=WeatherCity.get_minutely_rain_change,
        message_cls=TextMessage
    )