import filetype, base64

import abstract
from abstract.command import COMMAND_GROUP, group_only, cost, ask_for_wait
from abstract.bases.config import CONFIG
from abstract.message import GroupMessage, ImageMessage, ReplyMessage, TextMessage
from abstract.session import Session
from abstract.apis.table import GROUP_OPTION_TABLE

from .LLM import LLM, CHAT_AGENTS


@COMMAND_GROUP.register_command(('chat', ), info='与ai对话')
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
                                parts: list = message_part.to_args()
                                for prefix in COMMAND_GROUP.command_prefixes:
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

    character: LLM = CHAT_AGENTS[message.get_parts_by_type(TextMessage)[0].to_args()[1]]
    assert not character.r18 or GROUP_OPTION_TABLE.get(f'where id = {message.target.id}', attr='r18')[0] > 0, \
        '你所在的群聊的r18设置为0'
    message.reply_text(
        character.chat(session, format(message))
    )
    message.reply_text(f'本次请求消耗bot主约{character.cost: .2f}元')