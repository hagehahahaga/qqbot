from datetime import UTC

from abstract.bases.importer import itertools, time, numpy, pymysql, json, local_time

from PicImageSearch.sync import *

import abstract.message
from abstract.bases.custom_thread import CustomThreadGroup
from abstract.message import *
from abstract.bot import BOT
from abstract.command import COMMAND_GROUP, ask_for_wait, cost, group_only, authorize, private_only
from abstract.session import Session
from abstract.bases.exceptions import *
from abstract.apis.table import GROUP_OPTION_TABLE, NOTICE_SCHEDULE_TABLE, USER_TABLE


@COMMAND_GROUP.register_command(('search', '搜图', '以图搜图'), {'needed_type': ImageMessage}, '多API同时搜索')
@cost(2)
@ask_for_wait
def pic_searching(message: MESSAGE, session: Session, image: list[ImageMessage]):
    def pic_search(api, index: int):
        name = api.__class__.__name__
        try:
            result = api.search(url=input_url)
            if result.raw[index].thumbnail:
                result = result.raw[index]
            else:
                result = result.raw[index+1]
        except IndexError:
            message.reply_text(f'{name}搜索结果: ない')
        except TypeError as error:
            message.reply_text(f'{name}搜索错误: {error}')
        except Exception as error:
            message.reply_text(f'{name}未知错误: {error}')
        else:
            try:
                thumbnail = requests.get(
                    result.thumbnail,
                    headers=json.loads(pathlib.Path('./abstract/apis/headers.json').read_text())
                )
            except requests.RequestException:
                message.reply_text(
                    f'{name} 搜索结果:\n'
                    f'作者: {result.author if "author" in dir(result) else "ない"}\n'
                    f'出处: {result.url}\n'
                    f'预览图: {result.thumbnail.removeprefix("http://reverse-proxies.hagehaga.space/")}\n'
                )
            else:
                message.reply(
                    [
                        TextMessage(
                            f'{name} 搜索结果:\n'
                            f'作者: {result.author if "author" in dir(result) else "ない"}\n'
                            f'出处: {result.url}\n'
                            f'预览图: {result.thumbnail.removeprefix("http://reverse-proxies.hagehaga.space/")}\n'
                        ),
                        ImageMessage(
                            data=thumbnail.content
                        )
                    ]
                )

    input_url = image[0].url
    if not input_url:
        raise CommandCancel('获取图片失败!')
    apis = [
        (Ascii2D(bovw=True, proxies=CONFIG.commands_configs.pic_searching.ascii2d_proxy, verify_ssl=False), 1),
        (SauceNAO(api_key='bd4378a4695ff0145d32d950bdbe890a46387082'), 0),
        (BaiDu(), 0),
        (Yandex(), 0),
        (Iqdb(), 0),
        (Iqdb(True), 0)
    ]

    thread_group = CustomThreadGroup(pic_search, apis)
    try:
        thread_group.start()
        thread_group.join()
    except CommandCancel:
        thread_group.stop()
        completed_count = thread_group.completed_thread_count
        cost = int(completed_count / len(apis) * 2)
        if completed_count and cost < 1:
            cost = 1
        if cost:
            message.sender.points -= cost
            message.reply_text(f'部分搜索已完成, 消耗了 {cost} 个韭菜盒子.')
        raise

@COMMAND_GROUP.register_command(('random', '随机', '随机图', '随机涩图', '涩图', '多来点'), 1, '随机pixiv图')
@ask_for_wait
@cost(2)
def random_pic(message: MESSAGE, session: Session, args):
    def worker():
        nonlocal message, session, args, r18, retry_times
        if retry_times >= 3:
            raise CommandCancel('失败次数过多, 放弃.')
        retry_times += 1
        output = requests.get(
            url='https://api.lolicon.app/setu/v2?' +
                (
                    args[0] if args else
                    CONFIG.commands_configs.random_pic.default_tags
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
                    requests.get(output["urls"].get("regular", output["urls"]['original'])).content
                )
            )
        except IndexError:
            raise CommandCancel('无结果, 可能是你的xp太邪门了.')
        except (PIL.UnidentifiedImageError, requests.ConnectionError):
            message.reply_text('图片获取失败, 重试中...')
            worker()
            return
        image.putpixel((0, 0), image.getpixel((0, 1)))
        image_file = io.BytesIO()
        try:
            image.save(image_file, format='PNG')
            image_file.seek(0)
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
            image_file.close()
            message.reply_text('发送失败, 重试中...')
            LOG.WAR('Pic send failed. ')
            worker()

    if isinstance(message, GroupMessage):
        r18 = GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr='r18')[0]
    else:
        r18 = 0
    retry_times = 0

    worker()


@COMMAND_GROUP.register_command(('compress', '压缩', '压缩图'), {'needed_type': ImageMessage}, '一键电子包浆')
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


@COMMAND_GROUP.register_command(('option', '设置', '群设置', '群聊设置'), 1, '更改/查询机器人在此群聊的设置')
@authorize('admin')
@group_only
def option(message: MESSAGE, session: Session, args):
    match args:
        case []:
            return abstract.bot.help(message, session, ['option'])
        case [key, value]:
            assert key != 'trusted' or message.sender.role == 'operator', '本项仅operator可修改. 你在装你妈呢我就不明白了.'
            try:
                GROUP_OPTION_TABLE.set('id', message.target.id, key, value)
            except Exception as error:
                match error:
                    case pymysql.OperationalError(args=(1054, _)):
                        raise CommandCancel('错误: 设置项不存在.')
                    case pymysql.OperationalError(args=(3819, _)):
                        raise CommandCancel('错误: 本群不在白名单中或输入不合规.')
                    case _:
                        LOG.WAR(f'Group option {key} set failed.')
                        raise CommandCancel(f'错误: {error}.')

            option.__wrapped__(message, session, (key,))
        case [key]:
            try:
                message.reply_text(
                    '查询结果:\n'
                    f"  {key} - {GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr=key)[0]}"
                )
            except Exception as error:
                match error:
                    case pymysql.OperationalError(args=(1054, _)):
                        raise CommandCancel('错误: 查询项不存在.')
                    case _:
                        LOG.WAR(f'Group option {key} query failed.')
                        raise CommandCancel(f'错误: {error}.')
        case final:
            raise CommandCancel(f'参数 {final} 有误.')


@COMMAND_GROUP.register_command(('set', '设置'), 1, '更改机器人的私聊设置')
@private_only
def option_private(message: MESSAGE, session: Session, args):
    match args:
        case []:
            abstract.bot.help(message, session, ['set'])
        case [key, value]:
            assert key in ('todo_notice',), f'没有权限访问{key}.'
            try:
                USER_TABLE.set('id', message.sender.id, key, value)
            except Exception as error:
                match error:
                    case pymysql.OperationalError(args=(3819, _)):
                        raise CommandCancel('错误: 输入不合规.')
                    case _:
                        LOG.WAR(f'Group option {key} set failed.')
                        raise CommandCancel(f'错误: {error}.')
            else:
                message.reply_text(f'{key}已设置为{value}')
        case [key]:
            assert key in ('todo_notice',), f'没有权限访问{key}.'
            try:
                message.reply_text(f'设置项 {key} 值为 {USER_TABLE.get(f"where id = {message.sender.id}", attr=key)[0]}')
            except Exception as error:
                LOG.WAR(f'Group option {key} query failed.')
                raise CommandCancel(f'错误: {error}.')
        case final:
            raise CommandCancel(f'参数 {final} 有误.')


@COMMAND_GROUP.register_command(('points', '点数', '韭菜盒子'), info='查询韭菜盒子数')
def points(message: MESSAGE, session: Session):
    message.reply_text(
        f'你当前的韭菜盒子数为: {message.sender.points}.'
    )


@COMMAND_GROUP.register_command(('transfer', '转账'), 2, '转账')
def transfer(message: MESSAGE, session: Session, args):
    match args:
        case []:
            return abstract.bot.help(message, session, ['transfer'])
        case [*args, TextMessage(text=num)]:
            try:
                num = int(num)
            except ValueError:
                raise CommandCancel('输入的额度无法转换为数字!')
            match args:
                case [AtMessage(target=recipients), *_, AtMessage(target=target)]:
                    if message.sender.role != 'operator':
                        raise CommandCancel('只有操作员可以从其他用户账户转账!')
                    if recipients.points < num:
                        raise CommandCancel('转账人余额不足!')
                    recipients.points -= num
                    target.points += num

                case [AtMessage(target=target)]:
                    if message.sender.role != 'operator':
                        if message.sender.points < num:
                            raise CommandCancel('您的余额不足!')
                        message.sender.points -= num
                    target.points += num

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


@COMMAND_GROUP.register_command(('sign', '签到'), info='签到获取韭菜盒子')
def sign(message: MESSAGE, session: Session):
    from abstract.bases.importer import random
    if message.sender.sign_date == local_time().astimezone(UTC).date():
        message.reply_text('今日已签到过了!')
        return
    bonus = random.randint(5, 9)
    match random.randint(1, 100):
        case score if score <= 1:
            message.reply_text('大奖. +10')
            bonus += 10
        case score if score <= 10:
            message.reply_text('小奖. +3')
            bonus += 3

    message.sender.points += bonus
    message.sender.update_sign_date()
    message.reply_text(f'今日签到获得韭菜盒子: {bonus}个.')


@COMMAND_GROUP.register_command(('notice', '提醒'), 1, '提醒系统')
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
        case []:
            return abstract.bot.help(message, session, ['notice'])
        case ['add', text, time, *every]:
            if every:
                every = every[0]
                assert every in ('day', 'week')
            else:
                every = None
            if time.endswith('后'):
                time = time[:-1]
                assert time, '多久后没说'
                time = [time]
                mapping = {
                    ('天', '日'): 'days',
                    ('秒', '秒钟'): 'seconds',
                    ('分', '分钟'): 'minutes',
                    ('时', '小时'): 'hours',
                    ('周', '星期'): 'weeks'
                }
                mapping = dict(
                    itertools.chain.from_iterable(
                        (
                            (key, value) for key in keys
                        ) for keys, value in mapping.items()
                    )
                )
                for word in sorted(mapping, key=len, reverse=True):
                    new_time = []
                    for part in time:
                        if word in part and part not in mapping:
                            point = part.index(word)
                            new_time.append(part[:point])
                            new_time.append(word)
                            new_time.append(part[point+len(word):])
                            continue
                        new_time.append(part)
                    time = new_time
                while '' in time:
                    time.remove('')

                params = {}
                time_iter = iter(reversed(time))
                for part in time_iter:
                    try:
                        digit = next(time_iter)
                        params[mapping[part]] = float(digit)
                    except StopIteration:
                        message.reply_text(f'{part}前没有数字, 检查输入.')
                        return None
                    except ValueError:
                        message.reply_text(f'{digit}不是一个数字, 检查输入.')
                        return None

                time = datetime.datetime.now() + datetime.timedelta(**params)
            elif time == 'now':
                time = datetime.datetime.now()
            else:
                time = datetime.datetime.strptime(time, '%Y%m%d%H%M%S')
            NOTICE_SCHEDULE_TABLE.add(
                id,
                notice_type,
                time,
                text,
                every
            )

        case ['status']:
            message.reply_text(
                '查询结果:\n' +
                '\n'.join(
                    map(
                        lambda a: f'时间: {a[0].strftime('%Y%m%d%H%M%S')}, 每: {a[1]}, 内容: {a[2]}',
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

        case ['remove', time]:
            time = datetime.datetime.strptime(time, '%Y%m%d%H%M%S')
            NOTICE_SCHEDULE_TABLE.delete('(id, type, time)', (id, notice_type, time))

        case final:
            message.reply_text(f'匹配 {final} 失败, 检查输入.')
            return

    notice(message, session, ['status'])


@COMMAND_GROUP.register_command(('say', '说', '语录'), info='随机电棍语录')
@ask_for_wait
@cost(2)
def say(message: MESSAGE, session: Session):
    from abstract.bases.importer import random
    message.reply(
        RecordMessage(
            random.choice(
                list(pathlib.Path('extra/say').iterdir())
            )
        )
    )


@COMMAND_GROUP.register_command(('phantom', '幻影坦克'), {'needed_type': ImageMessage, 'needed_num': 2}, '幻影坦克图片生成')
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


@COMMAND_GROUP.register_command(('service', '服务'), 1, '服务系统')
@authorize('operator')
def service(message: MESSAGE, session: Session, args):
    try:
        match args:
            case []:
                return abstract.bot.help(message, session, ['service'])
            case ['status']:
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


@COMMAND_GROUP.register_command(('forge', '伪造'), 0, '伪造聊天记录')
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
