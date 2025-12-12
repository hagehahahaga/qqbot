from abstract.bases.importer import operator, last_commit, psutil, platform

import abstract
from abstract.command import CommandGroup, Command
from abstract.message import *
from abstract.service import Service
from abstract.session import SESSIONMANAGER, Session
from abstract.target import User, Group
from abstract.apis.frame_server import FRAME_SERVER
from abstract.apis.table import GROUP_OPTION_TABLE
from abstract.bases.log import LOG
from abstract.bases.exceptions import CommandCancel


class Bot:
    def __init__(
            self,
            frame_server: abstract.apis.frame_server.FrameServer,
            session_manager: abstract.session.SessionManager,
            id: int,
            must_at=True,
            command_prefixes=('', )
    ):
        self.frame_server = frame_server
        self.session_manager = session_manager
        self.id = id
        self.must_at = must_at
        self.command_prefixes = command_prefixes
        self.commands = CommandGroup()
        self.services: dict[str, Service] = {}

    def register_command(self, command_name: str | Iterable, type: int | dict[str, MESSAGE_PART | int] = 0, info=''):
        """
        Register commands that runs them handling messages

        :param command_name:
        :param type:
        0 - no arg needed;
        1 - string arg needed;
        2 - message part arg needed;
        {
            'needed_type': MESSAGE_PART,
            'needed_num': int = 1
        } - assigned message parts arg needed:
        :return: decorated method
        """
        def decorator(func):
            self.commands.add(Command(func, command_name, type, info))

            return func

        return decorator

    def register_service(self, service_name: str, auto_restart=False):
        """
        Register and run services

        :param service_name: Name of the service
        :param auto_restart: Whether to auto restart the service when it stops unexpectedly

        :return: decorated method
        """
        def decorator(func):
            service = Service(func, service_name, auto_restart)
            self.services[service_name] = service
            service.start()

            return func

        return decorator

    def router(self, data: dict):
        LOG.DEB(str(data))
        match data['post_type']:
            case 'message':
                self.message_handler(data)
            case 'notice':
                self.notice_handler(data)
            case 'request':
                self.request_handler(data)

    def message_handler(self, data: dict):
        message = Message(data)
        LOG.INF(f'{message.sender} said to {message.target}: {message.json["raw_message"]}')

        # 获取session
        session = self.session_manager.get_session(message.sender.id)

        # 获取指令名
        try:
            args = text_to_args(message.get_parts_by_type(TextMessage)[0].text)
            command_name, args = args[0], args[1:]
        except IndexError:
            command_name, args = '', []

        # 当消息为Private时始终为True, 否则只有匹配prefix时为True
        if not self.command_prefixes:
            is_command = True
        else:
            for command_prefix in self.command_prefixes:
                if command_name.startswith(command_prefix):
                    is_command = True
                    command_name = command_name.removeprefix(command_prefix)
                    break
            else:
                is_command = isinstance(message, PrivateMessage)
        if session.getting:
            session.pipe_put(message)
            return

        if isinstance(message, GroupMessage):
            if self.must_at and self.id not in map(
                    operator.attrgetter('target', 'id'),
                    message.get_parts_by_type(AtMessage)
            ):
                return
        elif isinstance(message, PrivateMessage):
            if message.sender.id not in map(
                    operator.itemgetter('user_id'),
                    self.frame_server.get_friend_list()
            ):
                return

        if session.lock.locked():
            session.handle(message, command_name, is_command)
            return

        if not is_command:
            return

        if not command_name:
            message.reply_text('我白银我最萌, s8我上我能夺冠, 职业选手都是帅逼.')
            return
        try:
            command = self.commands[command_name]
        except KeyError:
            message.reply_text(f'{command_name}不是一个可识别的指令, 检查输入.')
            return

        with session:
            LOG.INF(f'{message.sender} used {command_name}')
            session.command = command

            match command.type:
                case 0:
                    command(message, session)

                case 1:
                    command(message, session, args)

                case 2:
                    match message.messages:
                        case [abstract.message.AtMessage(), abstract.message.TextMessage(), *part_args] if self.must_at: ...
                        case [abstract.message.TextMessage(), *part_args]: ...
                        case final:
                            message.reply_text(f'匹配{final}失败, 检查输入.')
                            return
                    command(message, session, part_args)

                case {'needed_type': needed_type}:
                    needed_num = command.type.get('needed_num', 1)
                    input_type = message.get_parts_by_type(needed_type)

                    if isinstance(message.messages[0], ReplyMessage):
                        input_type.extend(message.messages[0].get_reply_message().get_parts_by_type(needed_type))

                    while (input_len := len(input_type)) < needed_num:
                        message.reply_text(f'此指令需要{needed_num}个{needed_type.NAME}, 你输入了{input_len}个, 继续输入.')
                        try:
                            message_got = session.pipe_get(message)
                        except CommandCancel as error:
                            message.reply_text(error.__str__())
                            return
                        if message_got.messages:
                            if isinstance(message_got.messages[0], ReplyMessage):
                                message_got = message_got.messages[0].get_reply_message()
                        input_type.extend(message_got.get_parts_by_type(needed_type))

                    input_type = input_type[:needed_num]
                    command(message, session, input_type)

    def notice_handler(self, data: dict):
        match data['notice_type']:
            case 'group_recall' if GROUP_OPTION_TABLE.get(f'where id = {data["group_id"]}', attr='recall_catch')[0]:
                GroupMessage(
                    [
                        AtMessage(data['operator_id']),
                        TextMessage(' 撤回了'),
                        AtMessage(data['user_id']),
                        TextMessage(f' 的消息:\n{self.frame_server.get_msg(data["message_id"])["raw_message"]}'),
                    ],
                    Group(data['group_id'])
                ).send()
            case 'group_decrease':
                GroupMessage(
                    [
                        TextMessage('人生自古谁无死？不幸的，'),
                        AtMessage(data['user_id']),
                        TextMessage(' 已经无法再与您互动，让我们默哀一普朗克时间，，，')
                    ],
                    Group(data['group_id'])
                ).send()
            case 'group_increase':
                GroupMessage(
                    [
                        AtMessage(data['user_id']),
                        TextMessage(' 进群了')
                    ],
                    Group(data['group_id'])
                ).send()
            case 'notify':
                match data['sub_type']:
                    case 'poke':
                        if data['target_id'] != CONFIG['bot_config']['id']:
                            return
                        if group_id := data.get('group_id'):
                            self.frame_server.poke(data['user_id'], group_id)
                        else:
                            self.frame_server.poke(data['user_id'])

    def request_handler(self, data: dict):
        match data['request_type']:
            case 'friend':
                self.frame_server.set_friend_add_request(data['flag'], True)
                PrivateMessage('输入 help 查看帮助.', User(data['user_id'])).send()
            case 'group' if data['sub_type'] == 'invite':
                self.frame_server.set_group_add_request(data['flag'], True)
                GroupMessage('大家好啊, 我是说的道理~', data['group_id']).send()


LOG.INF('Initializing bot...')
BOT = Bot(FRAME_SERVER, SESSIONMANAGER, **CONFIG['bot_config'])
LOG.INF('Bot initialized successfully.')


@BOT.register_command(('help', '帮助'), 1, '列出指令列表')
def help(message: MESSAGE, session: Session, args):
    match args:
        case [command]:
            match command:
                case 'search':
                    message.reply_text('支持api: Ascii2d, SauceNAO, Baidu, Yandex')
                case 'option':
                    message.reply_text(
                        '\noption <key> 查询, option <key> <value>设置'
                        '支持参数:\n'
                        '   r18 = 0:\n'
                        '       random取得的图片\n'
                        '       0 - 无r18, 1 - 仅r18, 2 - 混合\n'
                        '   recall_catch = 0:\n'
                        '       防撤回\n'
                        '       0 - 关, 1 - 开'
                    )
                case 'sign':
                    message.reply_text('randint(1,9) + %9: 3/ %1: 10')
                case 'stock':
                    message.reply_text(
                        '\n支持功能:\n'
                        '   status[ stock/commission]:\n'
                        '       查询个人状态以及股市状态\n'
                        '   sell/buy <price> <num>:\n'
                        '       发起交易\n'
                        '   cancel:\n'
                        '       取消委托中的交易'
                    )
                case 'random':
                    message.reply_text(
                        'tag格式参照: https://api.lolicon.app/#/setu?id=tag, 如: tag=萝莉|少女&tag=白丝|黑丝.'
                    )
                case 'notice':
                    message.reply_text(
                        '\n支持功能:\n'
                        '   status:\n'
                        '       查询当前进行中的定时提醒\n'
                        '   add [--time=now[\n'
                        '           %Y-%m-%d,%H:%M:%S |\n'
                        '           [--weeks=],[--days=],[--hours=],[--minutes=],[--seconds=]后\n'
                        '       ]\n'
                        '   ] [--text=] [--every=enum("day", "week"]:\n'
                        '       添加定时提醒, every决定是否每天/周提醒\n'
                        '   remove time:\n'
                        '       time格式%Y-%m-%d %H:%M:%S, 根据time删除定时提醒'
                    )
                case _:
                    message.reply_text('该项还没有文档.')
        case []:
            message.reply_text(
                '\n指令列表:\n' +
                '\n'.join(
                    map(
                        lambda a:f'{a.command_names}: {a.info}',
                        BOT.commands
                    )
                )
            )


@BOT.register_command(('version', '版本', '版本信息'), info='查看机器人开发信息')
def version(message: MESSAGE, session: Session):
    message.reply_text(
        '\n开发信息:\n'
        '   机器人代码: Python, 哈嗝哈哈哈嘎开发\n'
        '   QQ机器人框架: 无头NapCatQQ\n'
        '   机器人协议: Onebot, http\n'
        '   数据库使用: MySQL\n'
        '最近一次提交:\n'
        f'   哈希: {last_commit.hexsha}\n'
        f'   作者: {last_commit.author.name}\n'
        f'   时间: {last_commit.committed_datetime}\n'
        '   信息: \n'
        f'{last_commit.message.strip()}'
    )


@BOT.register_command(('status', '状态', '状态信息'))
def status(message: MESSAGE, session: Session):
    system = platform.system()
    message.reply_text(
        '当前状态:\n'
        f'  cpu:{psutil.cpu_percent()}%'
        f'  ({psutil.sensors_temperatures()["coretemp"][0].current if system == "Linux" else "当前平台不支持温度传感"}℃)\n'
        f'  dram:{psutil.virtual_memory().available / (1024 ** 3)}GiB可用'
    )
