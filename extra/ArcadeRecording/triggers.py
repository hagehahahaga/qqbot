from abstract.bases.importer import local_time

from .commands import arcade
from abstract.bases.exceptions import CommandCancel
from abstract.message import *
from abstract.session import Session, SESSION_MANAGER
from abstract.bot import BOT


def get_group_message_text(message: MESSAGE) -> str:
    """
    获取群消息的文本内容

    :param message: 消息对象
    :return: 文本内容，若不满足条件则返回空字符串
    """
    if not isinstance(message, GroupMessage):
        return ''
    text = message.get_parts_by_type(TextMessage)
    if not text:
        return ''
    return text[0].text


def get_arcade_num_condition(message: MESSAGE) -> bool:
    text = message.get_parts_by_type(TextMessage)
    if not text:
        return False
    text = text[0].text
    SUFFIEXES = ('几', 'j')
    for suffix in SUFFIEXES:
        if text.endswith(suffix):
            return True
    return False


@BOT.register_trigger(get_arcade_num_condition)
def get_arcade_num(message: MESSAGE, session: Session):
    SUFFIEXES = ('几', 'j')
    text = message.get_parts_by_type(TextMessage)[0].text
    for suffix in SUFFIEXES:
        if text.endswith(suffix):
            text = text[:-len(suffix)]
            break

    target = message.target if isinstance(message, GroupMessage) else message.sender

    if not text:
        if isinstance(target, Group):
            arcade(message, SESSION_MANAGER.get_session(message.sender), ['list'])
        if target.get_arcade_binding_hashes():
            arcade(message, SESSION_MANAGER.get_session(message.sender), ['binding','list'])
        return

    try:
        result = target.get_arcade_binding_num(text)
    except AssertionError:
        if isinstance(target, User):
            message.reply_text(f'没有绑定机厅为 {text}.')
            return
        try:
            result = target.get_arcade_num(text)
        except AssertionError:
            message.reply_text(f'没有名为 {text} 的机厅或绑定.')
            return

    if not any(result):
        message.reply_text(f'今天 {text} 还没有记录人数.')
        return

    message.reply_text(f'\n{text}{result[0]}\n{result[2]}记录于{result[1].strftime("%H点%M分 UTC%z")}')


def update_arcade_num_condition(message: MESSAGE) -> bool:
    text = get_group_message_text(message)
    digits = ''
    for letter in text[::-1]:
        if letter.isdigit():
            digits += letter
        else:
            break
    if not text:
        return False
    return bool(digits)


@BOT.register_trigger(update_arcade_num_condition)
def update_arcade_num(message: MESSAGE, session: Session):
    text = message.get_parts_by_type(TextMessage)[0].text

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
    arcade = text[:-len(digits)]
    if not plus is None:
        arcade = arcade[:-1]
    num = int(digits[::-1])

    try:
        result = message.target.get_arcade_num(arcade)[0]
    except AssertionError, IndexError:
        return
    if not result:
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
        timeout = 10
        message.reply_text(f'{arcade} {num}人的记录已寄存. {timeout}秒内发送undo取消提交, 发送push马上提交.')
        target_time = local_time() + datetime.timedelta(seconds=timeout)
        try:
            while local_time() < target_time:
                message_get = session.pipe_get(
                    message, False,
                    (target_time - local_time()).total_seconds()
                ).get_parts_by_type(TextMessage)
                if not message_get:
                    continue
                text = message_get[0].text
                match text:
                    case 'undo':
                        message.reply_text('记录未提交.')
                        return
                    case 'push':
                        break
        except CommandCancel:
            ...

    message.update_arcade_num(arcade, num)
    message.reply_text('记录已提交.')
