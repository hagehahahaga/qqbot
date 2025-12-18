import threading

from abstract.bases.importer import abc, itertools
from typing import Optional, Literal

from abstract.bases.exceptions import CommandCancel
from abstract.bases.log import LOG
from abstract.target import User
from abstract.bases.custom_thread import CustomThreadGroup
from abstract.session import SESSION_MANAGER
from abstract.message import GroupMessage, AtMessage, TextMessage
from config import CONFIG


class GameOver(BaseException):
    pass


class BaseGame(abc.ABC):
    NAME: str
    NEEDED_MEMBER_NUM: int
    STARTING_TEXT: str

    def __init__(self, game_manager: GameManager, owner: User):
        self._game_manager = game_manager
        self.members: list[User] = [owner, ]
        self.invite_thread_group: Optional[CustomThreadGroup] = None
        self.handle_thread_group: Optional[CustomThreadGroup] = None
        self.status: Literal['IDLE', 'INVITING', 'INVITE_FAIL', 'CANCELED', 'RUNNING', 'DONE'] = 'IDLE'
        self.winner : Optional[User] = None

    def add_member(self, member: User):
        self.members.append(member)

    def has_member(self, member: User) -> bool:
        return member in self.members

    def _invite(self, message: GroupMessage, target: User):
        assert target not in self.members
        session = SESSION_MANAGER.get_session(target)

        with session:
            reply = ''
            while reply != 'join':
                try:
                    reply = session.pipe_get(message, False).get_parts_by_type(TextMessage)
                except CommandCancel as e:
                    if e.text in ('用户取消输入.', '未继续输入.'):
                        self.status = 'INVITE_FAIL'
                    if self.invite_thread_group.status == 'RUNNING':
                        self.invite_thread_group.stop(0)
                    return False

                if reply:
                    reply = reply[0].to_args()[0]

            self.add_member(target)
        return True

    def invite_member(self, message: GroupMessage, targets: list[User]):
        try:
            assert len(targets) == self.NEEDED_MEMBER_NUM - 1, f'需要 {self.NEEDED_MEMBER_NUM - 1} 名玩家, 但提供了 {len(targets)} 名玩家.'
            assert self.status == 'IDLE', '游戏进行中或已完成.'
            assert len(set(t.id for t in targets)) == len(targets), '邀请列表中存在重复用户.'
            assert not message.sender.in_game_blacklists(targets), '你邀请的玩家中有将你拉黑的用户.'
            assert self.members[0] not in targets, '不能邀请房主自己加入游戏.'
            assert User(CONFIG['bot_config']['id']) not in targets, '不能邀请bot本体加入游戏.'
            invite_message = message.reply(
                *(AtMessage(target) for target in targets),
                TextMessage(' '),
                TextMessage(f'你被邀请参加游戏 {self.NAME} , 发送"join"以加入游戏, 发送"cancel"以拒绝邀请.')
            )
            self.invite_thread_group = CustomThreadGroup(self._invite, zip(itertools.repeat(invite_message), targets))
            self.status = 'INVITING'
            self.invite_thread_group.start()
            self.invite_thread_group.join()
        except CommandCancel:
            self._game_manager.free_game(self)
            self.status = 'CANCELED'
            self.invite_thread_group.stop(0)
            raise CommandCancel('游戏被发起者取消.')
        except Exception as e:
            self.status = 'INVITE_FAIL'
            self._game_manager.free_game(self)
            raise e

        if self.status == 'INVITE_FAIL':
            self._game_manager.free_game(self)
            raise CommandCancel('有用户未接受游戏邀请, 游戏取消.')

    @abc.abstractmethod
    def handle(self, message: GroupMessage):
        pass

    def runner(self, message: GroupMessage, target: User):
        session = SESSION_MANAGER.get_session(target)
        with session:
            while self.status == 'RUNNING':
                try:
                    message_got = session.pipe_get(message, False, None)
                    if self.status != 'RUNNING':
                        continue
                    self.handle(message_got)
                except CommandCancel:
                    if self.status == 'RUNNING':
                        self.cancel(message)
                    return
                except GameOver:
                    return
                except Exception as error:
                    message.reply_text(f'游戏出现错误: {error}')
                    LOG.ERR(error)
                    self.cancel(message)
                    return

        if session.getting:
            session.pipe_put(message_got)
            return

        from abstract.bot import BOT
        threading.Thread(target=BOT.router, args=(message_got.data,), daemon=True).start()

    def start(self, message: GroupMessage):
        self.status = 'RUNNING'
        self.handle_thread_group = CustomThreadGroup(self.runner, zip(itertools.repeat(message), self.members), kwargs=[])
        self.handle_thread_group.start()
        message.reply_text('游戏开始, 游戏中可以发送"cancel"以取消游戏.')
        message.reply_text(self.STARTING_TEXT)

    def cancel(self, message: GroupMessage):
        self.status = 'CANCELED'
        message.reply_text('游戏已被取消.')
        self._game_manager.free_game(self)

    def end(self):
        self.status = 'DONE'
        self._game_manager.free_game(self)
        if not self.winner:
            for member in self.members:
                member.draw_game(self.NAME)
            raise GameOver()

        for member in self.members:
            member.win_game(self.NAME) if member == self.winner else member.lose_game(self.NAME)
        raise GameOver()


class GameManager(dict):
    games = {}
    def __init__(self):
        super().__init__()

    def __getitem__(self, item) -> type[BaseGame]:
        return super().__getitem__(item)

    def has_member(self, member: User) -> Optional[BaseGame]:
        """
        检查成员是否已加入任何游戏.
        """
        for game in self.games.values():
            if game.has_member(member):
                return game
        return None

    def _new_game(self, owner: User, game_cls: type[BaseGame]) -> BaseGame:
        assert not isinstance(game_cls, BaseGame), 'Game class must be a subclass of BaseGame.'
        if self.has_member(owner):
            raise ValueError('The owner is already in a game.')

        game = game_cls(self, owner)
        self.games[owner.id] = game
        LOG.INF(f'New game {game_cls.NAME} created by user {owner}.')
        return game

    def get_game(self, owner: User, game_cls: Optional[type[BaseGame]] = None) -> BaseGame:
        if game := self.has_member(owner):
            return game
        return self._new_game(owner, game_cls)

    def free_game(self, game: BaseGame):
        self.games.pop(game.members[0].id)
        LOG.INF(f'Game {game.NAME} created by {game.members[0]} has been freed.')

    def register_game(self, game: type[BaseGame]):
        assert not isinstance(game, BaseGame), 'Game class must be a subclass of BaseGame.'
        self[game.NAME] = game
        return game


GAME_MANAGER = GameManager()