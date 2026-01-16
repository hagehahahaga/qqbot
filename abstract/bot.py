from abstract.bases.importer import operator, last_commit, psutil, platform, json, pathlib
from typing import Callable

import abstract
from abstract.command import COMMAND_GROUP
from abstract.game import GAME_MANAGER
from abstract.message import *
from abstract.service import Service
from abstract.session import SESSION_MANAGER, Session
from abstract.target import User, Group
from abstract.apis.frame_server import FRAME_SERVER
from abstract.apis.table import GROUP_OPTION_TABLE
from abstract.bases.log import LOG

# 加载帮助配置
HELP_TEXT = json.loads(pathlib.Path('help_text.json').read_text(encoding='utf-8'))


class Bot:
    def __init__(
            self,
            frame_server: abstract.apis.frame_server.FrameServer,
            session_manager: abstract.session.SessionManager,
            command_group: abstract.command.CommandGroup,
            id: int,
            must_at=True,
            command_prefixes=('', )
    ):
        self.frame_server = frame_server
        self.session_manager = session_manager
        self.command_group = command_group.set_prefixes(command_prefixes)
        self.id = id
        self.must_at = must_at
        self.services: dict[str, Service] = {}
        self.triggers: list[tuple[Callable[[MESSAGE], bool], Callable]] = []

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

    def register_trigger(self, condition: Callable[[MESSAGE], bool]):
        """
        注册条件触发器
        
        :param condition: 条件函数，接收MESSAGE对象，返回bool值
        :type condition: Callable[[MESSAGE], bool]
        
        :return: 装饰器
        """
        def decorator(func):
            self.triggers.append((condition, func))
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
        LOG.INF(f'{message.sender} said to {message.target}: {message.data["raw_message"]}')

        # 获取session
        session = self.session_manager.get_session(message.sender)

        # 获取指令名
        try:
            args = message.get_parts_by_type(TextMessage)[0].to_args()
            command_name, args = args[0], args[1:]
        except IndexError:
            command_name, args = '', []

        command = self.command_group.match(command_name, isinstance(message, GroupMessage))

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
            session.handle(message, command)
            return

        if command is None:
            for condition, func in self.triggers:
                if condition(message):
                    try:
                        func(message, session)
                    except Exception as e:
                        LOG.ERR(e)
                        raise e
            return

        if not command:
            message.reply_text('我白银我最萌, s8我上我能夺冠, 职业选手都是帅逼.')
            return

        if isinstance(command, str):
            message.reply_text(f'{command}不是一个可识别的指令, 检查输入.')
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
                    command(
                        message, session,
                        session.pipe_get_by_type(message, needed_type, command.type.get('needed_num', 1))
                    )

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
BOT = Bot(FRAME_SERVER, SESSION_MANAGER, COMMAND_GROUP, **CONFIG['bot_config'])
LOG.INF('Bot initialized successfully.')


@COMMAND_GROUP.register_command(('help', '帮助'), 1, '列出指令列表')
def help(message: MESSAGE, session: Session, args):
    match args:
        case [command]:
            if command in HELP_TEXT['commands']:
                help_content = HELP_TEXT['commands'][command]
                if isinstance(help_content, list):
                    help_text = '\n' + '\n'.join(help_content)
                else:
                    help_text = help_content
                message.reply_text(help_text)
            else:
                message.reply_text('该项还没有文档.')
        case []:
            message.reply_text(
                '\n指令列表:\n' +
                '\n'.join(
                    map(
                        lambda a:f'{a.command_names}: {a.info}',
                        BOT.command_group
                    )
                )
            )


@COMMAND_GROUP.register_command(('version', '版本', '版本信息'), info='查看机器人开发信息')
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


@COMMAND_GROUP.register_command(('status', '状态', '状态信息'))
def status(message: MESSAGE, session: Session):
    system = platform.system()
    message.reply_text(
        '当前状态:\n'
        f'  cpu:{psutil.cpu_percent()}%'
        f'  ({psutil.sensors_temperatures()["coretemp"][0].current if system == "Linux" else "当前平台不支持温度传感"}℃)\n'
        f'  dram:{psutil.virtual_memory().available / (1024 ** 3)}GiB可用'
    )


@COMMAND_GROUP.register_command(('game', '游戏'), 0 ,'游戏菜单')
def game_menu(message: MESSAGE, session: Session):
    text_args = message.get_parts_by_type(TextMessage)[0].to_args()[1:]
    match text_args:
        case []:
            return abstract.bot.help(message, session, ['game'])
        case ['list']:
            message.reply_text(
                '\n可用游戏列表:\n' +
                '\n'.join(
                    map(
                        lambda a: f'{a.NAME}: 需要{a.NEEDED_MEMBER_NUM}名玩家.',
                        GAME_MANAGER.values()
                    )
                )
            )
        case ['info', game_name]:
            assert game_name in GAME_MANAGER, f'游戏 {game_name} 不存在, 使用 "game list" 查看可用游戏.'
            target = message.get_parts_by_type(AtMessage)[:1]
            if not target:
                target = [AtMessage(message.sender)]
            target = target[0].target
            data = target.get_game_info(game_name)
            message.reply_text(
                f'玩家 {target} 的 {game_name} 信息:\n'
                f'   总游戏数: {data["count"]}\n'
                f'   胜利数: {data["win"]}\n'
                f'   胜率: {data["rate"]}'
            )
        case ['start', game_name]:
            assert game_name in GAME_MANAGER, f'游戏 {game_name} 不存在, 使用 "game list" 查看可用游戏.'
            game_type = GAME_MANAGER[game_name]
            targets = [
                part.target for part in session.pipe_get_by_type(message, AtMessage, game_type.NEEDED_MEMBER_NUM - 1)
            ]

            game = GAME_MANAGER.get_game(message.sender, game_type)
            game.invite_member(message, targets)
            game.start(message)
        case ['blacklist', 'add']:
            target = message.get_parts_by_type(AtMessage)[:1]
            assert target, '请@需要拉黑的用户.'
            message.sender.add_game_blacklist(message.sender)
            message.reply_text(f'已将用户 {target} 加入游戏黑名单.')
        case ['blacklist', 'remove']:
            target = message.get_parts_by_type(AtMessage)[:1]
            assert target, '请@需要移除拉黑的用户.'
            message.sender.remove_game_blacklist(message.sender)
            message.reply_text(f'已将用户 {target} 从游戏黑名单移除.')
        case ['blacklist']:
            blacklists = message.sender.get_game_blacklist()
            if not blacklists:
                message.reply_text('你的游戏黑名单为空.')
                return
            message.reply_text(
                '你的游戏黑名单:\n' +
                '\n'.join(
                    map(
                        lambda a: f'   {a}',
                        blacklists
                    )
                )
            )
        case final:
            message.reply_text(f'匹配{final}失败, 检查输入.')
