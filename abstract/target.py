import datetime
from datetime import UTC

from abstract.bases.importer import dispatch, json, local_time
from typing import Literal

from abstract.bases.config import CONFIG
from abstract.apis.frame_server import ONEBOT_SERVER
from abstract.apis.table import USER_TABLE, GROUP_OPTION_TABLE, GAME_DATA_TABLE


class User:
    role: Literal["member", "admin", "owner", "operator"]
    init_tables = [USER_TABLE, GAME_DATA_TABLE]
    """
    用户角色:
    - member: 普通成员
    - admin: 群管理员
    - owner: 群主
    - operator: Bot操作员（最高权限）
    """
    
    @dispatch
    def __init__(self, data: dict):
        self.id = data['user_id']
        self.name = data['nickname']
        self.role = data.get('role', 'member')
        if self.id in CONFIG.bot_config.operators:
            self.role = 'operator'
        for table in self.init_tables:
            if not table.find_exists('id', self.id):
                table.add(f'{self.id}' + ', DEFAULT' * (table.get_len() - 1))

    @dispatch
    def __init__(self, id: int | str):
        self.__init__(ONEBOT_SERVER.get_stranger_info(id))

    def __str__(self):
        return f'{self.name}({self.id})'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}(user_id: {self.id})> at {hex(id(self))}'

    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.id == value.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def register_func(cls, func):
        assert not hasattr(cls, func.__name__), f"注册失败!方法 {func.__name__} 已存在，覆盖需要使用override函数."
        setattr(cls, func.__name__, func)
        return func

    @classmethod
    def override(cls, func):
        assert hasattr(cls, func.__name__), f"注册失败! 原方法 {func.__name__} 不存在, 创建需要使用register_func函数."
        setattr(cls, func.__name__, func)
        return func

    @property
    def points(self) -> int:
        return int(USER_TABLE.get(f'where id = {self.id}', attr='points')[0])

    @points.setter
    def points(self, value: int):
        USER_TABLE.set(
            'id',
            self.id,
            'points',
            value
        )

    @property
    def sign_date(self) -> datetime.date:
        return USER_TABLE.get(f'where id = {self.id}', attr='sign_date')[0]

    @sign_date.setter
    def sign_date(self, value: datetime.date):
        USER_TABLE.set('id', self.id, 'sign_date', value)

    def update_sign_date(self):
        USER_TABLE.set('id', self.id, 'sign_date', local_time().astimezone(UTC).date())

    def game_data_exist(self, game: str) -> bool:
        return bool(
            GAME_DATA_TABLE.get(
                f'where id = {self.id}', attr=f'json_contains(json_keys(game_data), \'"{game}"\')'
            )[0]
        )

    def game_data_init(self, game: str):
        from abstract.game import GAME_MANAGER
        assert game in GAME_MANAGER, f'未知的游戏 {game}.'
        with GAME_DATA_TABLE as cursor:
            cursor.execute(
                f'update {cursor.table_name} '
                f'set game_data = json_set(game_data, "$.{game}", json_object("count", 0, "win", 0, "draw", 0))'
                f'where id = {self.id}'
            )

    @staticmethod
    def check_game_data(func):
        def decorated(self: User, game: str, *args, **kwargs):
            if not self.game_data_exist(game):
                self.game_data_init(game)
            return func(self, game, *args, **kwargs)

        return decorated

    @check_game_data
    def get_game_data(self, game: str) -> dict:
        return json.loads(
            GAME_DATA_TABLE.get(
                f'where id = {self.id}', attr=f'json_extract(game_data, "$.{game}")'
            )[0]
        )

    def get_game_info(self, game: str) -> dict:
        data = self.get_game_data(game)
        return {
            'count': data['count'],
            'win': data['win'],
            'rate': f"{(data['win'] / data['count'] * 100):.2f}%" if data['count'] > 0 else '0.00%'
        }

    @check_game_data
    def win_game(self, game: str):
        with GAME_DATA_TABLE as cursor:
            cursor.execute(
                f'update {cursor.table_name} '
                f'set game_data = json_set(game_data, '
                f'"$.{game}.count", json_extract(game_data, "$.{game}.count") + 1, '
                f'"$.{game}.win", json_extract(game_data, "$.{game}.win") + 1) '
                f'where id = {self.id}'
            )

    @check_game_data
    def draw_game(self, game: str):
        with GAME_DATA_TABLE as cursor:
            cursor.execute(
                f'update {cursor.table_name} '
                'set game_data = json_set(game_data, '
                f'"$.{game}.count", json_extract(game_data, "$.{game}.count") + 1, '
                f'"$.{game}.draw", json_extract(game_data, "$.{game}.draw") + 1) '
                f'where id = {self.id}'
            )

    @check_game_data
    def lose_game(self, game: str):
        with GAME_DATA_TABLE as cursor:
            cursor.execute(
                f'update {cursor.table_name} '
                'set game_data = json_set(game_data, '
                f'"$.{game}.count", json_extract(game_data, "$.{game}.count") + 1) '
                f'where id = {self.id}'
            )

    @property
    def game_blacklist(self) -> set[User]:
        return set(
            User(user_id) for user_id in json.loads(
                GAME_DATA_TABLE.get(
                    f'where id = {self.id}', attr='black_list'
                )[0]
            )
        )

    @game_blacklist.setter
    def game_blacklist(self, value: set[User]):
        value = [
            user.id for user in value
        ]
        GAME_DATA_TABLE.set('id', self.id, 'black_list', json.dumps(value))


class Group:
    def __init__(self, id):
        self.id = id
        self.name = ONEBOT_SERVER.get_group_info(id)['group_name']
        if not GROUP_OPTION_TABLE.find_exists('id', self.id):
            GROUP_OPTION_TABLE.add(str(self.id) + ',default' * (GROUP_OPTION_TABLE.get_len() - 1))

    @property
    def members(self) -> set[User]:
        return set(
            User(user_id) for user_id in ONEBOT_SERVER.get_group_member_list(self.id)
        )

    def __str__(self):
        return f'{self.name}({self.id})'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}(group_id: {self.id})> at {hex(id(self))}'

    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.id == value.id

    def __contains__(self, value: User) -> bool:
        return value in self.members

    @classmethod
    def register_func(cls, func):
        assert not hasattr(cls, func.__name__), f"注册失败!方法 {func.__name__} 已存在，覆盖需要使用override函数."
        setattr(cls, func.__name__, func)
        return func

    @classmethod
    def override(cls, func):
        assert hasattr(cls, func.__name__), f"注册失败! 原方法 {func.__name__} 不存在, 创建需要使用register_func函数."
        setattr(cls, func.__name__, func)
        return func
