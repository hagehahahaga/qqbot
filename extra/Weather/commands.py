from abstract.command import COMMAND_GROUP, cost, group_only, ask_for_wait
from abstract.message import MESSAGE, ImageMessage
from abstract.session import Session
from abstract.apis.table import GROUP_OPTION_TABLE
from abstract.bases.exceptions import CommandCancel

from .weather_city import WEATHER_CITY_MANAGER
from .exceptions import CityNotFound


@COMMAND_GROUP.register_command(('weather', '天气', '现在天气'), 1, '获取实时天气')
@cost(2)
@group_only
@ask_for_wait
def weather(message: MESSAGE, session: Session, args):
    match args:
        case []:
            city_name = ''
            method = 'now'
        case [*city_name, method]:
            if city_name:
                city_name = city_name[0]
            else:
                city_name = ''
        case _:
            message.reply_text(f'匹配 {args} 失败, 检查输入.')
            return

    if not city_name:
        city_name = GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr='city')[0]
        if not city_name:
            raise CommandCancel('未设置默认城市, 在命令后添加城市名, 或让管理员设置默认城市.')
        message.reply_text(f'未指定城市, 将使用群默认城市 {city_name}.')

    try:
        weather_city = WEATHER_CITY_MANAGER[city_name]
    except CityNotFound:
        raise CommandCancel(f'未能找到城市 {city_name}. 如为默认城市则让管理员更正, 或手动输入.')

    weather_city.flush_cache()

    match method:
        case 'now':
            message.reply_text(
                '\n' +
                weather_city.get_weather_now_text()
            )
        case 'hourly':
            message.reply(ImageMessage(weather_city.get_weather_hourly()))
        case 'daily':
            message.reply(ImageMessage(weather_city.get_weather_daily()))
        case 'today':
            message.reply_text(
                '\n' +
                weather_city.get_weather_day_text()
            )
        case 'tomorrow':
            message.reply_text(
                '\n' +
                weather_city.get_weather_tomorow_text()
            )
        case 'minutely':
            rain_change = weather_city.get_minutely_rain_change()
            if rain_change:
                message.reply_text('\n' + rain_change)
            else:
                message.reply_text('\n未来30分钟内降水情况无变化或暂无数据.')
        case _:
            message.reply_text(f'匹配 {args} 失败, 检查输入.')
