from abstract.bases.importer import datetime, functools, threading, copy
from abstract.bases.importer import getopt, io, random, time
from abstract.bases.importer import filetype, numpy, pymysql
from abstract.bases.importer import json, PIL

import PIL.Image
from third.PicImageSearch.sync import *

from abstract.message import *
from abstract.bot import BOT
from abstract.session import Session
from extra.chat_ai import LLM, CHAT_AIs
from abstract.bases.exceptions import *
from abstract.apis.table import GROUP_OPTION_TABLE, STOCK_TABLE, NOTICE_SCHEDULE_TABLE
from abstract.apis.table import NULL
from abstract.bases.interruptible_tasks.interruptible_request import InterruptibleRequest
from extra.vits_speaker import SPEAKER_MANAGER
from extra.weather_city import WEATHER_CITY_MANAGER, WeatherCity
from abstract.bases.one_time_var import OneTimeVar


def ask_for_wait(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        args[0].reply_text('别急')
        func(*args, **kwargs)

    return decorated


def cost(cost: int):
    def decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            message = args[0]
            if message.sender.get_points() < cost:
                message.reply_text(
                    '\n韭菜盒子不足!\n'
                    f'我早上本来应该吃 {cost} 个韭菜盒子, 饱饱的.\n'
                    '那我缺的这个这个营养这一块的, 谁给我补啊?\n'
                )
                return

            func(*args, **kwargs)

            message.sender.add_points(-cost)
            message.reply_text(f'本次请求消耗 {cost} 个韭菜盒子, 贼jb好吃.')

        return decorated

    return decorator


def group_only(func):
    @functools.wraps(func)
    def decorated(*args, **kwargs):
        assert type(args[0]) is GroupMessage, '此指令仅在群聊中可用!'
        func(*args, **kwargs)

    return decorated


def authorize(min_level: str):
    level_list = ['member', 'admin', 'owner', 'operator']

    def decorator(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            assert level_list.index(args[0].sender.role) >= level_list.index(min_level), \
                f'执行此指令最低需要{min_level}权限.'

            func(*args, **kwargs)

        return decorated

    return decorator


@BOT.register_command(('search', '搜图', '以图搜图'), {'needed_type': ImageMessage}, '多API同时搜索')
@cost(2)
@ask_for_wait
def pic_searching(message: MESSAGE, session: Session, image: list[ImageMessage]):
    @BOT.error_handler
    def pic_search(input_image: bytes, api, index: int, api_name: str, message: MESSAGE):
        try:
            result = api.search(file=input_image)
            if result.raw[index].thumbnail:
                result = result.raw[index]
            else:
                result = result.raw[index+1]
        except IndexError:
            message.reply_text(f'{api_name}搜索结果: ない')
        except TypeError as error:
            message.reply_text(f'{api_name}搜索错误: {error}')
        except Exception as error:
            message.reply_text(f'{api_name}未知错误: {error}')
        else:
            message.reply(
                [
                    TextMessage(
                        f'{api_name} 搜索结果:\n'
                        f'作者: {result.author if "author" in dir(result) else "ない"}\n'
                        f'出处: {result.url}\n'
                        f'预览图: {result.thumbnail.removeprefix("http://reverse-proxies.hagehaga.space/")}\n'
                    ),
                    ImageMessage(
                        data=requests.get(
                            result.thumbnail,
                            headers=json.loads(pathlib.Path('./abstract/apis/headers.json').read_text())
                        ).content
                    )
                ]
            )

    input_image = image[0].image
    if not input_image:
        raise CommandCancel('获取图片失败!')

    apis = {
        'ascii2d': [
            Ascii2D(
                bovw=True,
                base_url='http://reverse-proxies.hagehaga.space/https%3A%2F%2Fascii2d.net%2F'
            ),
            1
        ],
        'saucenao': [
            SauceNAO(api_key='bd4378a4695ff0145d32d950bdbe890a46387082'),
            0
        ],
        'baidu': [
            BaiDu(),
            0
        ],
        'yandex': [
            Yandex(),
            0
        ],
        'Iqdb': [
            Iqdb(),
            0
        ],
        'Iqdb_3d': [
            Iqdb(True),
            0
        ]
    }

    threads = [
        threading.Thread(
            target=pic_search,
            args=(
                input_image,
                apis[key][0],
                apis[key][1],
                key,
                message
            )
        ) for key in apis.keys()
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


@BOT.register_command(('random', '随机', '随机图', '随机涩图', '涩图', '多来点'), 1, '随机pixiv图', cancelable=True)
@ask_for_wait
@cost(2)
def random_pic(message: MESSAGE, session: Session, args):
    if type(message) is GroupMessage:
        r18 = GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr='r18')[0]
    else:
        r18 = 0
    output = InterruptibleRequest(session).run(
        url='https://api.lolicon.app/setu/v2?' +
            (
                args[0] if args else
                CONFIG.get('commands_configs', {}).get('random_pic', {}).get('default_tags', '')
            ) +
            '&size=regular&size=original&'
            'excludeAI=true&'
            f'r18={r18}'
    ).json()

    if output['error']:
        raise CommandCancel(f'图床错误: {output["error"]}')

    try:
        output = output['data'][0]
        image = PIL.Image.open(
            io.BytesIO(
                InterruptibleRequest(session).run(output["urls"].get("regular", output["urls"]['original'])).content
            )
        )
    except IndexError:
        raise CommandCancel('无结果, 可能是你的xp太邪门了.')
    except (PIL.UnidentifiedImageError, requests.ConnectionError):
        message.reply_text('图片获取失败, 重试中...')
        random_pic.__wrapped__.__wrapped__(message, session, args)
        return
    image.putpixel((0, 0), image.getpixel((0, 1)))
    image_file = io.BytesIO()
    try:
        image.save(image_file, format='PNG')
        image_file.seek(0)
        try:
            message.reply(
                [
                    TextMessage(
                        text=f'作者: {output["author"]}\n'
                             f'标题: {output["title"]}\n'
                             f'pid: {output["pid"]}\n'
                             f'url: {output["urls"]["original"]}'
                    ),
                    ImageMessage(
                        data=image_file.read()
                    )
                ]
            )
        except SendFailure:
            message.reply_text('发送失败, 重试中...')
            LOG.WAR('Pic send failed. ')
            random_pic.__wrapped__.__wrapped__(message, session, args)
    finally:
        image_file.close()


@BOT.register_command(('compress', '压缩', '压缩图'), {'needed_type': ImageMessage}, '一键电子包浆')
@ask_for_wait
def compress(message: MESSAGE, session: Session, args: list[ImageMessage]):
    input_image = args[0].image
    if not input_image:
        raise CommandCancel('获取图片失败!')

    try:
        image = PIL.Image.open(io.BytesIO(input_image)).convert('RGB')
    except PIL.UnidentifiedImageError:
        raise CommandCancel('无法识别的图像格式.')
    image.save(output := io.BytesIO(), 'JPEG', quality=10)
    message.reply(ImageMessage(data=output.getvalue()))


@BOT.register_command(('option', '设置', '群设置', '群聊设置'), 1, '更改/查询机器人在此群聊的设置')
@authorize('admin')
@group_only
def option(message: MESSAGE, session: Session, args):
    match args:
        case [key, value]:
            assert key != 'trusted' or message.sender.role == 'operator', '本项仅operator可修改. 你在装你妈呢我就不明白了.'
            try:
                GROUP_OPTION_TABLE.set('id', message.target.id, key, value)
            except Exception as error:
                match error:
                    case pymysql.OperationalError(args=(1054, x)):
                        message.reply_text(f'错误: 设置项不存在.')
                    case pymysql.OperationalError(args=(3819, x)):
                        message.reply_text(f'错误: 本群不在白名单中或输入不合法.')
                    case _:
                        LOG.WAR(f'Group option {key} set failed.')
                        message.reply_text(f'错误: {error}.')

            option.__wrapped__(message, session, (key,))
        case [key]:
            try:
                message.reply_text(
                    '查询结果:\n'
                    f"  {key} - {GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr=key)[0]}"
                )
            except Exception as error:
                match error:
                    case pymysql.OperationalError(args=(1054, x)):
                        message.reply_text(f'错误: 查询项不存在.')
                    case _:
                        LOG.WAR(f'Group option {key} query failed.')
                        message.reply_text(f'错误: {error}.')
        case final:
            message.reply_text(f'参数 {final} 有误!')


@BOT.register_command(('points', '点数', '韭菜盒子'), info='查询韭菜盒子数')
def points(message: MESSAGE, session: Session):
    message.reply_text(
        f'你当前的韭菜盒子数为: {message.sender.get_points()}.'
    )


@BOT.register_command(('transfer', '转账'), 2, '转账')
@authorize('operator')
def transfer(message: MESSAGE, session: Session, args):
    match args:
        case [*args, TextMessage(text=num)]:
            try:
                num = int(num)
            except ValueError:
                raise CommandCancel('输入的额度无法转换为数字!')
            match args:
                case [AtMessage(target=recipients), TextMessage(), AtMessage(target=target)]:
                    if recipients.get_points() < num:\
                        raise CommandCancel('转账人余额不足!')
                    recipients.add_points(-num)
                    target.add_points(num)

                case [AtMessage(target=target)]:
                    target.add_points(num)

                case final:
                    message.reply_text(f'匹配 {final} 失败, 检查输入.')
                    return

            message.reply(
                [
                    AtMessage(target=target),
                    TextMessage(f' 的韭菜盒子增加{num}个!')
                ]
            )
        case final:
            message.reply_text(f'匹配 {final} 失败, 检查输入.')
            return


@BOT.register_command(('sign', '签到'), info='签到获取韭菜盒子')
def sign(message: MESSAGE, session: Session):
    if message.sender.get_sign_date().strftime('%Y%m%d') == time.strftime('%Y%m%d'):
        message.reply_text('今日已签到过了!')
        return
    points = random.randint(5, 9)
    match random.randint(1, 100):
        case score if score <= 1:
            message.reply_text('大奖. +10')
            points += 10
        case score if score <= 10:
            message.reply_text('小奖. +3')
            points += 3

    message.sender.add_points(points)
    message.sender.update_sign_date()
    message.reply_text(f'今日签到获得韭菜盒子: {points}个.')


@BOT.register_command(('lottery', '彩票', '抽奖'), info='5个韭菜盒子购买一个韭菜盒子彩票')
@cost(5)
def lottery(message: MESSAGE, session: Session):
    if CONFIG["next_lottery_time"] > time.strftime('%Y%m%d%H%M%S'):
        raise CommandCancel('接盘侠还未赶来...')

    CONFIG['lottery_pool'] += 5
    match random.randint(1, 100):
        case score if score <= 1:
            message.reply_text(f'特大奖来袭! 奖池清空, +{CONFIG["lottery_pool"]}. 无语, 典型的特大男人思维.')
            message.sender.add_points(CONFIG["lottery_pool"])
            CONFIG["lottery_pool"] = 20
        case score if score <= 10:
            message.reply_text('大奖. +15')
            message.sender.add_points(20)
            CONFIG['lottery_pool'] -= 20
        case score if score <= 20:
            message.reply_text('小奖. +5')
            message.sender.add_points(10)
            CONFIG['lottery_pool'] -= 10
        case score if score <= 50:
            message.reply_text('不亏. +0')
            message.sender.add_points(5)
            CONFIG['lottery_pool'] -= 5
        case _:
            message.reply_text('未中奖...')

    if CONFIG["lottery_pool"] < 0:
        CONFIG["next_lottery_time"] = (time.strftime('%Y%m%d%H') + str(time.localtime().tm_min + 5) +
                                       time.strftime('%S'))
        CONFIG["lottery_pool"] = 0
        message.reply_text('彩票店破产跑路了! 接盘侠预计在 5 分钟后赶来.')
    message.reply_text(f'当前奖池: {CONFIG["lottery_pool"]}个.')


@BOT.register_command(('stock', '股票'), 1, '股票系统')
def stock(message: MESSAGE, session: Session, args):
    date = time.strftime('%Y-%m-%d')
    commission = message.sender.get_commission()
    trade = message.sender.get_trade()
    STOCK_TABLE.set(
        'id', CONFIG["robot_id"], 'commission_time', f"'{time.strftime('%Y-%m-%d %H:%M:%S')}'"
    )
    if str(commission['time']).split(' ')[0] < date and commission['type'] != 'none':
        message.sender.cancel_commission()
        message.reply_text('过期交易委托已取消!')
    if str(trade['time']).split(' ')[0] < date:
        message.reply_text(
            '\n昨日收益:\n'
            f'  韭菜盒子收入: {message.sender.get_points_sold()}'
            f'  股票收入: {message.sender.get_stocks_bought()}'
        )
        message.sender.store_points_sold()
        message.sender.store_stocks_bought()
        message.sender.update_trade(0, 0)

    match args:
        case ['status', *args]:
            match args:
                case []:
                    message.reply_text(
                        '\n当前状态:\n'
                        f'  持有股票: {message.sender.get_stocks()}\n'
                        f'  今日股票购入: {message.sender.get_stocks_bought()}\n'
                        f'  今日收益: {message.sender.get_points_sold()}\n'
                        f'  最后一次交易时间: {trade["time"]}\n'
                        f'  最后一次交易价格: {trade["price"]}\n'
                        f'  最后一次交易数量: {trade["num"]}'
                    )
                case ['stock']:
                    trade = User(id=STOCK_TABLE.get('ORDER BY trade_time desc', attr='id')[0]).get_trade()
                    message.reply_text(
                        '\n当前股市状态:\n'
                        f'  最后一次交易价格: {trade["price"]}\n'
                    )
                case ['commission']:
                    commission = message.sender.get_commission()
                    if commission['type'] == 'none':
                        message.reply_text('当前没有交易委托中')
                        return
                    message.reply_text(
                        '\n当前交易委托:\n'
                        f'  类型: {commission["type"]}\n'
                        f'  价格: {commission["price"]}\n'
                        f'  数量: {commission["num"]}'
                        f'  时间: {commission["time"]}\n'
                    )
                case [final]:
                    message.reply_text(f'{final} 不是可以查询的数据!')
                case final:
                    message.reply_text(f'匹配 {final} 失败, 检查输入.')
            return

        case [action, price, num] if action in ('buy', 'sell'):
            if commission['type'] != 'none':
                message.reply_text('你现在仍有一个交易委托进行中!')
                return
            try:
                price = int(price)
                num = int(num)
            except ValueError:
                message.reply_text('输入的参数无法转换为数字!')
                return

        case ['cancel']:
            message.sender.cancel_commission()
            message.reply_text('已有的交易委托已撤销.')
            return
        case final:
            message.reply_text(f'匹配 {final} 失败, 检查输入.')
            return

    match action:
        case 'buy':
            if price * num > message.sender.get_points() + message.sender.get_points_sold():
                message.reply_text('流动资金不足!')
                return
        case 'sell':
            if num > message.sender.get_stocks():
                message.reply_text('可卖出股票不足!')
                return

    message.sender.set_commission(action, price, num)
    while target_id := STOCK_TABLE.get(
            f"where (commission_type, date(commission_time)) = ('{'sell' if action == 'buy' else 'buy'}', curdate())"
            f"and commission_price {'<=' if action == 'buy' else '>'} {price}",
            f"order by commission_price {'asc' if action == 'buy' else 'desc'}, commission_time asc",
            attr='id'
    )[0]:
        target = User(id=target_id)
        target_commission = target.get_commission()
        if num < target_commission['num']:
            deal_num = num
        else:
            deal_num = target_commission['num']

        num -= deal_num
        message.sender.achieve_commission(target_commission['price'], deal_num)
        message.reply_text(f' 你以 {target_commission["price"]}韭菜盒子/股 的价格 {action} 了 {deal_num}股.')
        target.achieve_commission(target_commission['price'], deal_num)
        if not num:
            break
    else:
        message.reply_text(f'交易还剩 {num}股 未完成, 交易委托中...')


@BOT.register_command(('notice', '提醒'), 1, '提醒系统')
def notice(message: MESSAGE, session: Session, args):
    match type(message):
        case abstract.message.GroupMessage:
            id = message.target.id
            notice_type = 'group'
            assert message.sender.role in ('admin', 'owner', 'operator'), \
                '群聊中此指令仅管理员/操作员可用!'

        case abstract.message.PrivateMessage:
            id = message.sender.id
            notice_type = 'private'

    match args:
        case ['add', *args]:
            args = dict(
                getopt.getopt(
                    args,
                    '',
                    ['time=', 'text=', 'every=']
                )[0]
            )
            notice_time = args.get('--time', 'now')
            if notice_time.endswith('后'):
                offset = dict(
                    map(
                        lambda a: (a[0][2:], int(a[1])),
                        getopt.getopt(
                            notice_time[:-1].split(','),
                            '',
                            ['days=', 'seconds=', 'minutes=', 'hours=', 'weeks=']
                        )[0]
                    )
                )
                notice_time = (datetime.datetime.now() + datetime.timedelta(**offset)).strftime('%Y-%m-%d %H:%M:%S')
            elif notice_time == 'now':
                notice_time = time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                notice_time = ' '.join(notice_time.split(','))
            NOTICE_SCHEDULE_TABLE.add(
                id,
                notice_type,
                notice_time,
                args.get('--text', NULL),
                args.get('--every', NULL)
            )

        case ['status']:
            message.reply_text(
                '查询结果:\n' +
                '\n'.join(
                    map(
                        lambda a: f'时间: {a[0]}, 每: {a[1]}, 内容: {a[2]}',
                        NOTICE_SCHEDULE_TABLE.get_all(
                            f'where (id, type) = ({id}, "{notice_type}")',
                            attr='time, every, text'
                        )
                    )
                )
            )
            return

        case ['remove', 'all']:
            NOTICE_SCHEDULE_TABLE.delete('(id, type)', (id, notice_type))

        case ['remove', *args]:
            notice_time = ' '.join(args)
            NOTICE_SCHEDULE_TABLE.delete('(id, type, time)', (id, notice_type, notice_time))

        case final:
            message.reply_text(f'匹配 {final} 失败, 检查输入.')
            return

    notice(message, session, ['status'])


@BOT.register_command(('say', '说', '语录'), info='随机电棍语录')
@ask_for_wait
@cost(2)
def say(message: MESSAGE, session: Session):
    message.reply(
        RecordMessage(
            random.choice(
                list(pathlib.Path('./say').iterdir())
            )
        )
    )


@BOT.register_command(('chat', ), info='与ai对话', cancelable=True)
@group_only
@cost(3)
@ask_for_wait
def chat(message: GroupMessage, session: Session):
    def format(message: GroupMessage) -> list[dict]:
        output = []
        for part in message.split_when(lambda a: isinstance(a, ImageMessage | ReplyMessage)):
            match type(part):
                case _ if isinstance(part, list):
                    text = message.sender.__str__() + ': '
                    for message_part in part:
                        match type(message_part):
                            case abstract.message.AtMessage:
                                if message_part.target.id == CONFIG["robot_id"]:
                                    continue
                                text += message_part.target.__str__()
                            case abstract.message.TextMessage:
                                parts: list = text_to_args(message_part.text)
                                for prefix in BOT.command_prefixes:
                                    if parts[0].startswith(prefix) and parts[0][1:] == 'ai':
                                        parts = parts[2:]
                                text += ' '.join(parts)
                            case final:
                                raise TypeError(f'Unsupported type {final} for function "ai"!')
                    output.append(
                        {
                            'type': 'text',
                            'text': text
                        }
                    )
                case abstract.message.ImageMessage:
                    output.extend(
                        [
                            {
                                'type': 'text',
                                'text': message.sender.__str__() + ': '
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:{filetype.image_match(part.image).MIME};'
                                           f'base64,{base64.b64encode(part.image).decode()}'
                                }
                            }
                        ]
                    )
                case abstract.message.ReplyMessage:
                    output.extend(
                        [
                            {
                                'type': 'text',
                                'text': '`'
                            }
                        ] +
                        format(part.get_reply_message()) +
                        [
                            {
                                'type': 'text',
                                'text': '`'
                            }
                        ]
                    )

        return output

    character: LLM = CHAT_AIs[text_to_args(message.get_parts_by_type(TextMessage)[0].text)[1]]
    assert not character.r18 or GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr='r18')[0] > 0, \
        '你所在的群聊的r18设置为0'
    message.reply_text(
        character.chat(session, format(message))
    )
    message.reply_text(f'本次请求消耗bot主约{character.cost: .2f}元')


@BOT.register_command(('phantom', '幻影坦克'), {'needed_type': ImageMessage, 'needed_num': 2}, '幻影坦克图片生成')
@cost(2)
@ask_for_wait
def phantom_tank(message: MESSAGE, session: Session, args: list[ImageMessage]):
    white_image, black_image = args
    black_image_pil = PIL.Image.open(io.BytesIO(black_image.image))

    # 设置亮度系数
    a = 10  # 前景图像亮度
    b = 5  # 背景图像亮度

    # 获取背景图像的尺寸
    w_b, h_b = black_image_pil.size

    # 将前景图像缩放到背景图像的尺寸
    # 转换为numpy数组
    array_f = numpy.array(
        PIL.Image.open(
            io.BytesIO(white_image.image)
        ).resize((w_b, h_b), PIL.Image.Resampling.LANCZOS)
    )
    array_b = numpy.array(black_image_pil)

    # 创建新图像数组
    new_image_array = numpy.zeros((h_b, w_b, 4), dtype=numpy.uint8)

    # 提取前景图像和背景图像的RGB分量
    r_f, g_f, b_f = array_f[..., 0], array_f[..., 1], array_f[..., 2]
    r_b, g_b, b_b = array_b[..., 0], array_b[..., 1], array_b[..., 2]

    # 应用亮度系数
    r_f = r_f * (a / 10)
    g_f = g_f * (a / 10)
    b_f = b_f * (a / 10)

    r_b = r_b * (b / 10)
    g_b = g_b * (b / 10)
    b_b = b_b * (b / 10)

    # 计算差值
    delta_r = r_b - r_f
    delta_g = g_b - g_f
    delta_b = b_b - b_f

    # 计算新像素的透明度
    a_new = numpy.clip(
        255 + (
                4 * delta_r +
                8 * delta_g +
                6 * delta_b +
                ((delta_r - delta_b) * (r_b + r_f)) / 256 +
                (delta_r ** 2 - delta_b ** 2) / 512
        ) / (
                2 * (8 + 255 / 256 + (delta_r - delta_b) / 256)
        ),
        0,
        255
    ).astype(numpy.uint8)

    # 计算新像素的RGB分量
    mask = a_new > 0
    a_new = numpy.clip(a_new, 1e-8, 255).astype(numpy.uint8)
    # 赋值给新图像数组
    new_image_array[..., 0] = numpy.where(mask, 255 * r_b * b / 10 / a_new, 0).astype(numpy.uint8)
    new_image_array[..., 1] = numpy.where(mask, 255 * g_b * b / 10 / a_new, 0).astype(numpy.uint8)
    new_image_array[..., 2] = numpy.where(mask, 255 * b_b * b / 10 / a_new, 0).astype(numpy.uint8)
    new_image_array[..., 3] = a_new

    # 保存并回复图像
    new_image = PIL.Image.fromarray(new_image_array, 'RGBA')
    output_bytes = io.BytesIO()
    new_image.save(output_bytes, format='PNG')
    message.reply(
        ImageMessage(
            data=output_bytes.getvalue()
        )
    )


@BOT.register_command(('service', '服务'), 1, '服务系统')
@authorize('operator')
def service(message: MESSAGE, session: Session, args):
    try:
        match args:
            case ['status'] | []:
                message.reply_text(
                    '\n' +
                    '\n'.join(
                        map(
                            lambda a: f'{a}运行状态为: {a.is_alive()}, 自动重启: {a.auto_restart}',
                            BOT.services.values()
                        )
                    )
                )
                return
            case ['status', service]:
                ...
            case ['option', service, attribute, value]:
                try:
                    service.__setattr__(attribute, value)
                except AttributeError as error:
                    LOG.WAR(error)
                    message.reply_text(f'错误: {error}')
            case ['start', service]:
                BOT.services[service].start()
            case ['stop', service]:
                BOT.services[service].stop()
            case ['restart', service]:
                BOT.services[service].stop()
                BOT.services[service].start()
            case _:
                message.reply_text(f'匹配 {args} 失败, 检查输入.')
                return

        service_got = BOT.services[service]
        message.reply_text(f'{service}运行状态为: {service_got.is_alive()}, 自动重启: {service_got.auto_restart}')
    except KeyError:
        LOG.WAR(f'服务 {service} 不存在.')
        message.reply_text(f'服务 {service} 不存在.')


@BOT.register_command(('tts', 'ai语音'), 1, 'ai语音', cancelable=True)
@cost(2)
@ask_for_wait
def TTS(message: MESSAGE, session: Session, args):
    match args:
        case [speaker, *text]:
            text = ' '.join(text)
        case final:
            message.reply_text(f'匹配{final}失败, 检查输入.')
            return

    message.reply(
        RecordMessage(SPEAKER_MANAGER[speaker].TTS(session, text))
    )


@BOT.register_command(('svc', 'ai变音', '变音', '变声'), {'needed_type': RecordMessage, 'needed_num': 1}, 'ai变音', cancelable=True)
@cost(2)
@ask_for_wait
def SVC(message: MESSAGE, session: Session, args: list[RecordMessage]):
    try:
        command_args = text_to_args(message.get_parts_by_type(TextMessage)[0].text)
        speaker = command_args[1]
        try:
            pitch = float(command_args[2])
        except IndexError:
            pitch = None
    except IndexError:
        raise CommandCancel('未指定speaker.')

    message.reply(
        RecordMessage(
            SPEAKER_MANAGER[speaker].SVC(session, args[0].record, pitch)
        )
    )


@BOT.register_command(('forge', '伪造'), 0, '伪造聊天记录')
def forge_chat(message: MESSAGE, session: Session):
    content: list[NodeMessage] = []

    while True:
        message.reply_text('发送AtMessage | qqid指定发送人, 发送complete结束添加.')

        match session.pipe_get(message).messages:
            case [AtMessage(target=target)]:
                ...
            case [TextMessage(text='complete')]:
                break
            case [TextMessage(text=target)]:
                try:
                    target = User(int(target))
                except ValueError:
                    message.reply_text('不是一个qq号.')
                    continue
            case final:
                message.reply_text(f'匹配 {final} 失败, 检查输入.')
                continue

        message.reply_text('发送消息指定发送内容.')
        content.append(NodeMessage(target, session.pipe_get(message).messages))

    message.reply(
        content
    )


@BOT.register_command(('weather', '天气', '现在天气'), 1, '获取实时天气')
@cost(2)
@group_only
@ask_for_wait
def weather(message: MESSAGE, session: Session, args):
    option = OneTimeVar(None)
    args_temp = copy.copy(args)
    try:
        if 'hourly' in args_temp:
            option.value = 'hourly'
            args_temp.remove('hourly')
        if 'today' in args_temp:
            option.value = 'today'
            args_temp.remove('today')
        if 'now' in args_temp:
            option.value = 'now'
            args_temp.remove('now')
    except RuntimeError:
        raise CommandCancel(f'参数{args}错误, 检查输入.')

    if len(args_temp) > 1:
        raise CommandCancel(f'参数{args}错误, 检查输入.')

    if args_temp:
        city = args_temp[0]
    else:
        city = GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr='city')[0]
        if not city:
            raise CommandCancel('未设置默认城市, 在命令后添加城市名, 或让管理员设置默认城市.')
        message.reply_text(f'未指定城市, 将使用群默认城市 {city}.')

    try:
        weather_city = WEATHER_CITY_MANAGER[city]
    except CityNotFound:
        raise CommandCancel(f'未能找到城市 {city}. 如为默认城市则让管理员更正, 或手动输入.')

    match option.value:
        case None | 'now':
            message.reply_text(
                '\n' +
                weather_city.get_weather_now_text()
            )
        case 'hourly':
            message.reply(ImageMessage(weather_city.get_weather_hourly()))
        case 'today':
            message.reply_text(
                '\n' +
                weather_city.get_weather_today_text()
            )
