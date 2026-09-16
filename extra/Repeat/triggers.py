from abstract.bot import BOT
from abstract.message import GroupMessage, MESSAGE, TextPart
from abstract.session import Session
from extra.Repeat.repeater import REPEATER


def message_listen_condition(message: GroupMessage) -> bool:
    if not isinstance(message, GroupMessage):
        return False

    if not message.target.auto_repeat:
        return False

    if not message.parts:
        return False

    for part in message.parts:
        if not isinstance(part, TextPart):
            return False

    return True


@BOT.register_trigger(message_listen_condition)
def message_listen(message: MESSAGE, session: Session):
    REPEATER.handle(message)
