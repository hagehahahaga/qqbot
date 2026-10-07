import datetime
from datetime import UTC

from abstract.bases.importer import dispatch, json, local_time
from typing import Literal

from abstract.bases.config import CONFIG
from abstract.apis.frame_server import ONEBOT_SERVER
from abstract.apis.table import USER_TABLE, GROUP_OPTION_TABLE, GAME_DATA_TABLE


class User:
    # 构造 User 时需确保已存在记录的数据表, 缺失则自动补一行
    init_tables = [USER_TABLE, GAME_DATA_TABLE]
    registered_options: list[str] = []

    @dispatch
    def __init__(self, data: dict):
        self.id = data['user_id']
        self.name = data['nickname']
        # 角色: member 普通成员 / admin 群管理员 / owner 群主 / operator Bot操作员(最高权限)
        self.role: Literal["member", "admin", "owner", "operator"] = data.get('role', 'member')
        if self.id in CONFIG.bot_config.operators:
            self.role = 'operator'
        for table in self.init_tables:
            if not table.find_exists(id=self.id):
                # 只提供主键, 其余列交给表定义里的 DEFAULT
                table.add(id=self.id)

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
    def register_attr(cls, func):
        assert not hasattr(cls, func.__name__), f"注册失败! 方法 {func.__name__} 已存在"
        setattr(cls, func.__name__, func)
        return func

    @classmethod
    def register_option(cls, option_name: str) -> property:
        assert USER_TABLE.have_key(option_name), f'The table {USER_TABLE.name} has no column {option_name}. Have you forgot to init.sql?'
        @property
        def option(self):
            return USER_TABLE.get('where id = %s', self.id, option_name)[0]

        @option.setter
        def option(self, value):
            USER_TABLE.set(
                'where id = %s',
                self.id,
                **{option_name: value}
            )

        option.__name__ = option_name

        cls.registered_options.append(option_name)
        return cls.register_attr(option)  # type: ignore[arg-type]

    @property
    def points(self) -> int:
        return int(USER_TABLE.get('where id = %s', self.id, 'points')[0])

    @points.setter
    def points(self, value: int):
        USER_TABLE.set(
            'where id = %s',
            self.id,
            points=value
        )

    @property
    def sign_date(self) -> datetime.date:
        return USER_TABLE.get('where id = %s', self.id, 'sign_date')[0]

    @sign_date.setter
    def sign_date(self, value: datetime.date):
        USER_TABLE.set(
            'where id = %s',
            self.id,
            sign_date=value
        )

    def update_sign_date(self):
        USER_TABLE.set(
            'where id = %s',
            self.id,
            sign_date=local_time().astimezone(UTC).date()
        )

    def game_data_exist(self, game: str) -> bool:
        return bool(
            GAME_DATA_TABLE.get(
                'where id = %s', self.id, f'json_contains(json_keys(game_data), \'"{game}"\')'
            )[0]
        )

    def game_data_init(self, game: str):
        from abstract.game import GAME_MANAGER
        assert game in GAME_MANAGER, f'未知的游戏 {game}.'
        with GAME_DATA_TABLE as cursor:
            cursor.execute(
                f'update {cursor.table_name} '
                'set game_data = json_set(game_data, %s, json_object("count", 0, "win", 0, "draw", 0)) '
                'where id = %s',
                (f'$.{game}', self.id)
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
                'where id = %s', self.id, f'json_extract(game_data, "$.{game}")'
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
                'set game_data = json_set(game_data, '
                '%s, json_extract(game_data, %s) + 1, '
                '%s, json_extract(game_data, %s) + 1) '
                'where id = %s',
                (
                    f'$.{game}.count', f'$.{game}.count',
                    f'$.{game}.win', f'$.{game}.win',
                    self.id,
                )
            )

    @check_game_data
    def draw_game(self, game: str):
        with GAME_DATA_TABLE as cursor:
            cursor.execute(
                f'update {cursor.table_name} '
                'set game_data = json_set(game_data, '
                '%s, json_extract(game_data, %s) + 1, '
                '%s, json_extract(game_data, %s) + 1) '
                'where id = %s',
                (
                    f'$.{game}.count', f'$.{game}.count',
                    f'$.{game}.draw', f'$.{game}.draw',
                    self.id,
                )
            )

    @check_game_data
    def lose_game(self, game: str):
        with GAME_DATA_TABLE as cursor:
            cursor.execute(
                f'update {cursor.table_name} '
                'set game_data = json_set(game_data, '
                '%s, json_extract(game_data, %s) + 1) '
                'where id = %s',
                (
                    f'$.{game}.count', f'$.{game}.count',
                    self.id,
                )
            )

    @property
    def game_blacklist(self) -> set[User]:
        return set(
            User(user_id) for user_id in json.loads(
                GAME_DATA_TABLE.get(
                    'where id = %s', self.id, 'black_list'
                )[0]
            )
        )

    @game_blacklist.setter
    def game_blacklist(self, value: set[User]):
        value = [
            user.id for user in value
        ]
        GAME_DATA_TABLE.set(
            'where id = %s',
            self.id,
            black_list=json.dumps(value)
        )

class Group:
    registered_options: list[str] = []

    def __init__(self, id: int):
        self.id = id
        self.name = ONEBOT_SERVER.get_group_info(id)['group_name']
        if not GROUP_OPTION_TABLE.find_exists(id=self.id):
            GROUP_OPTION_TABLE.add(id=self.id)

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

    def __hash__(self) -> int:
        return hash(self.id)

    def __contains__(self, value: User) -> bool:
        return value in self.members

    @classmethod
    def register_attr(cls, func):
        assert not hasattr(cls, func.__name__), f"注册失败! 方法 {func.__name__} 已存在."
        setattr(cls, func.__name__, func)
        return func

    @property
    def trusted(self):
        return GROUP_OPTION_TABLE.get('where id = %s', self.id, 'trusted')[0]

    @trusted.setter
    def trusted(self, value):
        GROUP_OPTION_TABLE.set(
            'where id = %s',
            self.id,
            trusted=value
        )

    @classmethod
    def register_option(cls, option_name: str) -> property:
        assert GROUP_OPTION_TABLE.have_key(option_name), f'The table {GROUP_OPTION_TABLE.name} has no column {option_name}. Have you forgot to init.sql?'
        @property
        def option(self):
            return GROUP_OPTION_TABLE.get('where id = %s', self.id, option_name)[0]

        @option.setter
        def option(self, value):
            GROUP_OPTION_TABLE.set(
                'where id = %s',
                self.id,
                **{option_name: value}
            )
        option.__name__ = option_name
        cls.registered_options.append(option_name)
        return cls.register_attr(option)  # type: ignore[arg-type]


for option in ('r18', 'recall_catch', 'city', 'night_disturb'):
    Group.register_option(option)
