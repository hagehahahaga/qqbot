from operator import attrgetter

from abstract.bases.importer import local_time
from abstract.bases.exceptions import CommandCancel, SessionTransfer
from abstract.message import *
from abstract.session import Session, SESSION_MANAGER, InputTimeout
from abstract.bot import BOT

from .arcade import Arcade
from .cab import Cab
from .commands import arcade


def get_group_message_text(message: MESSAGE) -> str:
    """
    获取群消息的文本内容

    :param message: 消息对象
    :return: 文本内容，若不满足条件则返回空字符串
    """
    text = message.get_parts_by_type(TextPart)
    if not text:
        return ''
    return text[0].text


def get_arcade_num_condition(message: MESSAGE) -> bool:
    text = get_group_message_text(message)
    SUFFIEXES = ('几', 'j')
    for suffix in SUFFIEXES:
        if text.endswith(suffix):
            return True
    return False


@BOT.register_trigger(get_arcade_num_condition)
def get_arcade_num(message: MESSAGE, session: Session):
    SUFFIEXES = ('几', 'j')
    text = message.get_parts_by_type(TextPart)[0].text
    for suffix in SUFFIEXES:
        if text.endswith(suffix):
            text = text[:-len(suffix)]
            break

    target = message.target if isinstance(message, GroupMessage) else message.sender

    if not text:
        session = SESSION_MANAGER.get_session(message.sender)
        if isinstance(target, Group):
            with session:
                arcade(message, session, ['list'])
        if target.arcade_bindings:
            with session:
                arcade(message, session, ['binding', 'list'])
        return

    for binding in target.arcade_bindings:
        if text in binding.names:
            result: Arcade = binding.arcade
            break
    else:
        if isinstance(target, User):
            message.reply_text(f'没有绑定机厅为 {text}.')
            return

        try:
            result = Arcade(target, text)
        except AssertionError:
            message.reply_text(f'没有名为 {text} 的机厅或绑定.')
            return

    if result.num is None:
        message.reply_text(f'今天 {text} 还没有记录人数.')
        return

    others = result.num - sum(num for num in map(attrgetter("num"), result.cabs) if num)

    message.reply_text(
        f'\n{text}{result.num}\n' +
        '\n'.join(
            (
                f'{cab.name}: {"未记录人数" if cab.num is None else cab.num}, 预计'
                f'{2.5 * cab.tracks * cab.num / cab.slot * (2 if cab.must_pickup else 1):.0f}' +
                (f' - {2.5 * (cab.tracks + 1) * cab.num / cab.slot:.0f}' if cab.pickup_bonus else '') +
                '分钟1pc'
            ) for cab in result.cabs
        ) +
        (f'\n剩余{others}人未记录' if others and others != result.num else '') +
        f'\n{result.update_user}记录于{result.update_time.strftime("%H点%M分 UTC%z")}'
    )


def update_arcade_num_condition(message: MESSAGE) -> bool:
    if not isinstance(message, GroupMessage):
        return False
    text = get_group_message_text(message)
    digits = ''
    for letter in text[::-1]:
        if letter.isdecimal():
            digits += letter
        else:
            break
    if not text:
        return False
    return bool(digits)


@BOT.register_trigger(update_arcade_num_condition)
def update_arcade_num(message: GroupMessage, session: Session):
    text = message.get_parts_by_type(TextPart)[0].text

    digits = ''
    plus: Optional[bool] = None  # 判断是否加减, None为报数, True为加, 反之为减
    for letter in text[::-1]:
        if letter.isdigit():
            digits += letter
            continue
        match letter:
            case '+' | '加':
                plus = True
            case '-' | '减':
                plus = False
        break
    arcade_name = text[:-len(digits)]
    if not plus is None:
        arcade_name = arcade_name[:-1]
    num = int(digits[::-1])

    try:
        arcade: Arcade = Arcade(message.target, arcade_name)
    except AssertionError:
        return

    result = arcade.num
    if result is None:
        result = 0

    if plus:
        num += result
    elif plus is False:
        num = result - num

    if num > 255:
        message.reply_text('开玩笑呢? 怎么可能这么多人?')
        return
    if num < 0:
        message.reply_text(f'现在才{result}个人. 负数人数是有棍母吗?')
        return

    with session:
        timeout = 30
        message.reply_text(f'{arcade.name} {num}人的记录已寄存. {timeout}秒内发送cancel取消提交, 发送push马上提交. 可以继续发送 机台名+人数 记录机台人数.')
        cabs_nums = {}
        while True:
            try:
                message_got = session.pipe_get(
                    message,
                    False,
                    timeout,
                    condition=lambda a: a.parts[0].text == 'push' or a.parts[0].text[
                        -1].isdecimal() if a.parts and isinstance(a.parts[0], TextPart) else False
                )
                text = message_got.get_parts_by_type(TextPart)[0].text

                if text == 'push':
                    break

                splited: list[list[str]] = [['']]
                isdecimal = False
                for char in text:
                    if char.isdecimal() != isdecimal:
                        if not (isdecimal := char.isdecimal()):
                            splited.append([])
                        splited[-1].append(char)
                        continue

                    splited[-1][-1] += char

                for text, headcount in splited:
                    headcount = int(headcount)
                    if headcount > 255:
                        message_got.reply_text(f'根本没有{text}这么多人的机厅, 跳过.')
                        continue
                    cab = Cab(arcade.hash, text)
                    if not cab.exists:
                        message_got.reply_text(f'机台{text}未记录, 跳过.')
                        continue

                    cabs_nums[text] = headcount

                cab_sum = sum(cabs_nums.values())
                message_got.reply_text(
                    '目前已记录的机台人数:\n' +
                    '\n'.join(
                        f'{text}: {num}人' for text, num in cabs_nums.items()
                    ) +
                    (
                        '\n值得注意的是, '
                        f'机台记录人数 {cab_sum} 加起来超过机厅人数 {num}'
                        ', 确定没有数错吗?' if cab_sum > num else ''
                    )
                )
            except SessionTransfer:
                session.defer()
            except InputTimeout:
                break
            except CommandCancel:
                message.reply_text('记录未提交.')
                return

    arcade.num = num
    arcade.update_user = message.sender
    arcade.update_time = local_time()
    for cab, headcount in cabs_nums.items():
        Cab(arcade.hash, cab).num = headcount
    message.reply_text('记录已提交.')
