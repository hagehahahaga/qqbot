from abstract.bases.importer import abc, base64, pathlib, requests, dispatch, Iterable, typing

from abstract.bases.config import CONFIG
from abstract.target import User, Group
from abstract.apis.frame_server import FRAME_SERVER
from abstract.bases.log import LOG


class BaseMessagePart(abc.ABC):
    NAME: str
    @abc.abstractmethod
    def get_json(self): ...


class RecordMessage(BaseMessagePart):
    NAME = '语音消息'
    @dispatch
    def __init__(self, file: pathlib.Path):
        self.record = file.read_bytes()

    @dispatch
    def __init__(self, record: bytes):
        self.record = record

    def get_json(self):
        return {
            'type': 'record',
            'data': {
                'file': f'base64://{base64.urlsafe_b64encode(self.record).decode()}'
            }
        }


class ReplyMessage(BaseMessagePart):
    NAME = '回复消息'
    def __init__(self, id: int):
        self.id = id

    def get_reply_message(self):
        return Message(
            FRAME_SERVER.get_msg(
                self.id
            )
        )

    def get_json(self):
        return {
            'type': 'reply',
            'data': {
                'id': self.id
            }
        }


class AtMessage(BaseMessagePart):
    NAME = '@消息'
    def __init__(self, target: User):
        assert type(target) is User
        self.target = target

    def get_json(self):
        return {
            'type': 'at',
            'data': {
                'qq': str(self.target.id)
            }
        }

    def __repr__(self):
        return f'<{self.__class__.__name__} @{self.target}>'


class TextMessage(BaseMessagePart):
    NAME = '文本消息'
    def __init__(self, text: str):
        self.text: str = text

    def get_json(self):
        return {
            'type': 'text',
            'data': {
                'text': self.text
            }
        }

    def to_args(self) -> list[str]:
        return list(
            filter(
                lambda a: a,
                self.text.split(' ')
            )
        )

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.text}>'


class ImageMessage(BaseMessagePart):
    NAME = '图片消息'
    def __init__(self, data: bytes = None, url: str = None):
        self.data = data
        self.url = url
        assert data or url, 'None has been entered.'

    @property
    def image(self):
        if self.data:
            return self.data
        if self.url:
            self.data = requests.get(self.url).content
            return self.data
        raise ValueError('The image neither has data nor url!')

    def get_json(self):
        if self.data:
            return {
                'type': 'image',
                'data': {
                    'file': f'base64://{base64.urlsafe_b64encode(self.image).decode()}'
                }
            }
        else:
            return {
                'type': 'image',
                'data': {
                    'file': self.url
                }
            }


class FaceMessage(BaseMessagePart):
    NAME = '表情消息'
    def __init__(self, id: str):
        self.id = id

    def get_json(self):
        return {
            'type': 'face',
            'data': {
                'id': self.id
            }
        }


class NodeMessage(BaseMessagePart):
    NAME = '节点消息'
    def __init__(self, sender: User, content: list['MESSAGE_PART']):
        self.sender = sender
        self.content = content

    def get_json(self):
        return {
            'type': 'node',
            'data': {
                'user_id': self.sender.id,
                'nickname': self.sender.name,
                'content': list(
                    map(
                        lambda a: a.get_json(),
                        self.content
                    )
                )
            }
        }


MESSAGE_PART = RecordMessage | ReplyMessage | AtMessage | TextMessage | ImageMessage | NodeMessage


class BaseMessage(abc.ABC):
    send_api: classmethod
    target: User | Group

    def __init__(self, data):
        self.data = data
        self.sender = User(
            data['sender']
        )
        self.message_id = data['message_id']
        self.messages = []
        for message_part in data['message']:
            match message_part['type']:
                case 'reply':
                    message_part = [ReplyMessage(message_part['data']['id'])]
                case 'at':
                    message_part = [AtMessage(
                        target=User(int(message_part['data']['qq']))
                    )]
                case 'text':
                    message_part = [TextMessage(message_part['data']['text'])]
                case 'image':
                    url = '/'.join(['http:'] + message_part['data']['url'].split('/')[1:])

                    message_part = [ImageMessage(url=url)]
                case 'record':
                    message_part = [RecordMessage(
                        FRAME_SERVER.get_record(message_part['data']['file'])
                    )]
                case 'face':
                    message_part = [FaceMessage(message_part['data']['id'])]
                case 'forward':
                    message_part = map(
                        lambda a: Message(a).get_node(),
                        FRAME_SERVER.get_forward_msg(
                            message_part['data']['id']
                        )
                    )
                case 'json':
                    ...
                case final:
                    raise ValueError(f'Uncased message type {final}!')
            self.messages.extend(message_part)

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.sender} -> {self.target}: {self.get_json()}> at {hex(id(self))}'

    def get_json(self):
        return list(
            map(
                lambda a: a.get_json(),
                self.messages
            )
        )

    def get_node(self):
        return NodeMessage(self.sender, self.messages)

    def send(self):
        message = get_message(self.send_api(message=self))
        LOG.INF(f'Sent to {message.target}:  {message.data["raw_message"]}')
        return message

    @abc.abstractmethod
    def reply(self, messages: list | MESSAGE_PART) -> MESSAGE | None: ...

    def reply_text(self, text: str) -> MESSAGE:
        return self.reply(
            TextMessage(
                text=text
            )
        )

    def get_parts_by_type(self, part_type: type[MESSAGE_PART]) -> list[MESSAGE_PART]:
        return list(
            filter(
                lambda a: isinstance(a, part_type),
                self.messages
            )
        )

    def split_when(self, condition) -> typing.Generator[list[MESSAGE_PART] | MESSAGE_PART]:
        for out in split_when(self.messages, condition):
            yield out

    def delete(self):
        FRAME_SERVER.delete_message(self.message_id)
        LOG.DEB(f'Deleted message {self}')


class PrivateMessage(BaseMessage):
    send_api = FRAME_SERVER.send_private_msg

    @dispatch
    def __init__(self, data: dict):
        super().__init__(data)
        self.target = User(CONFIG['bot_config']['id'])

    @dispatch
    def __init__(self, text: str | None, target: User):
        if text is None:
            text = 'None'
        self.__init__([TextMessage(text)], target)

    @dispatch
    def __init__(self, messages: list | MESSAGE_PART, target: User):
        if isinstance(messages, MESSAGE_PART):
            messages = [messages]
        self.messages = messages
        self.target = target
        self.sender = User(CONFIG['bot_config']['id'])

    @dispatch
    def reply(self, message: list[NodeMessage]) -> MESSAGE:
        return PrivateMessage(
            message,
            self.sender
        ).send()

    @dispatch
    def reply(self, message: RecordMessage) -> MESSAGE | None:
        try:
            return PrivateMessage(
                message,
                self.sender
            ).send()
        except (requests.exceptions.InvalidURL, KeyError):
            return None

    @dispatch
    def reply(self, messages: list | MESSAGE_PART) -> MESSAGE:
        if not isinstance(messages, Iterable):
            messages = [messages]
        return PrivateMessage(
            [
                ReplyMessage(
                    id=self.message_id
                ),
            ] + messages,
            self.sender
        ).send()

    @dispatch
    def reply(self, *messages: MESSAGE_PART):
        return self.reply(
            list(messages)
        )

    def reply_text(self, text: str) -> MESSAGE:
        return super().reply_text(text.removeprefix('\n'))


class GroupMessage(BaseMessage):
    send_api = FRAME_SERVER.send_group_msg

    @dispatch
    def __init__(self, data: dict):
        super().__init__(data)
        self.target = Group(data['group_id'])

    @dispatch
    def __init__(self, text: str | None, target: Group):
        if text is None:
            text = 'None'
        self.__init__([TextMessage(text)], target)

    @dispatch
    def __init__(self, messages: list | MESSAGE_PART, target: Group):
        if isinstance(messages, MESSAGE_PART):
            messages = [messages]
        self.messages = messages
        self.target = target
        self.sender = User(CONFIG['bot_config']['id'])

    @dispatch
    def reply(self, message: list[NodeMessage]) -> MESSAGE:
        return GroupMessage(
            message,
            self.target
        ).send()

    @dispatch
    def reply(self, message: RecordMessage) -> MESSAGE | None:
        try:
            return GroupMessage(
                message,
                self.target
            ).send()
        except (requests.exceptions.InvalidURL, KeyError):
            return None

    @dispatch
    def reply(self, messages: list | MESSAGE_PART) -> MESSAGE:
        if not type(messages) is list:
            messages = [messages]
        return GroupMessage(
            [
                ReplyMessage(
                    id=self.message_id
                ),
                AtMessage(
                    target=self.sender
                ),
                TextMessage(
                    text=' '
                )
            ] + messages,
            self.target
        ).send()

    @dispatch
    def reply(self, *messages: MESSAGE_PART):
        return self.reply(
            list(messages)
        )


class Message:
    @dispatch
    def __new__(cls, data: dict):
        match data['message_type']:
            case 'private':
                return PrivateMessage(data)
            case 'group':
                return GroupMessage(data)

    @dispatch
    def __new__(cls, message: list | MESSAGE_PART, target: User | Group):
        match target:
            case User():
                return PrivateMessage(message, target)
            case Group():
                GroupMessage(message, target)


MESSAGE = PrivateMessage | GroupMessage


def get_message(message_id):
    return Message(
        FRAME_SERVER.get_msg(
            message_id
        )
    )


def split_when(inpu, condition) -> typing.Generator[list[MESSAGE_PART] | MESSAGE_PART]:
    output = []
    for part in inpu:
        if condition(part):
            if output:
                yield output
                output = []
            yield part
            continue
        output.append(part)

    if output:
        yield output
