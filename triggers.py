from abstract.bases.exceptions import CommandCancel
from abstract.bases.importer import local_time, datetime
from abstract.message import *
from abstract.session import Session
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
    text = get_group_message_text(message)
    if not text:
        return False
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

    result = message.target.get_arcade_num(text)
    if not result:
        message.reply_text(f'此群未设置机厅或别名 {text}.')
        return

    if not any(result):
        message.reply_text(f'{text} 还没有记录过人数.')
        return

    message.reply_text(f'\n{text}{result[0]}\n{result[1].strftime("%H点%M分 UTC%z")}数据')

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
    for letter in text[::-1]:
        if letter.isdigit():
            digits += letter
        else:
            break
    arcade = text[:-len(digits)]
    num = int(digits[::-1])

    result = message.target.get_arcade_num(arcade)
    if not result:
        return
    if num > 255:
        message.reply_text('开玩笑呢? 怎么可能这么多人?')

    with session:
        message.target.update_arcade_num(arcade, num)
        timeout = 10
        message.reply_text(f'{arcade}人数已记录为{num}. {timeout}秒内发送undo来取消记录, 发送push马上提交记录.')
        get_time = local_time()
        target_time = get_time + datetime.timedelta(seconds=timeout)
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
                        message.target.update_arcade_num(arcade, *result)
                        message.reply_text('记录已还原.')
                        return
                    case 'push':
                        break
        except CommandCancel:
            ...

    message.reply_text('记录已提交.')
