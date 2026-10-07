import datetime
import json
from datetime import UTC
from typing import Optional

from plum import dispatch

from abstract.bases.cached_property import cached_property
from abstract.bases.importer import today_7am
from abstract.target import User, Group

from .tables import ARCADES_TABLE, ARCADES_CABS_TABLE
from .cab import Cab


class Arcade:
    @dispatch
    def __init__(self, hash: bytes):
        self.hash = hash

        if not self.exists:
            return

        if self.update_time and self.update_time < today_7am():
            self.num = None
            self.update_time = None
            self.update_user = None
            for cab in self.cabs:
                cab.num = None

    @dispatch
    def __init__(self, group: Group, name: str):
        result = ARCADES_TABLE.get(
            'where group_id = %s and (json_contains(subnames, json_quote(%s)) or name = %s)',
            (group.id, name, name),
            'hash'
        )
        assert result, f'{group} 没有 {name} 这个机厅或别名.'
        self.__init__(result[0])

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Arcade):
            return False

        return value.hash == self.hash

    def __str__(self) -> str:
        return f'{self.name}({self.group})'

    @property
    def exists(self) -> bool:
        return ARCADES_TABLE.find_exists(hash=self.hash)

    @cached_property
    def group(self):
        # group_id 列是 decimal, PyMySQL 返回 Decimal, 需转成 int 再交给 Group
        group_id = ARCADES_TABLE.get(
            'where hash = %s',
            self.hash,
            'group_id'
        )[0]

        return Group(int(group_id))

    @cached_property
    def name(self) -> str:
        return ARCADES_TABLE.get(
            'where hash = %s',
            self.hash,
            'name'
        )[0]

    @cached_property
    def subnames(self) -> tuple[str, ...]:
        return tuple(json.loads(ARCADES_TABLE.get('where hash = %s', self.hash, 'subnames')[0]))

    @subnames.setter
    def subnames(self, value: tuple[str, ...]):
        assert len(set(value)) == len(value), '有重复命名.'
        deltas = set(value) - set(self.subnames)
        for delta in deltas:
            assert delta not in self.group.arcade_names, '有重复命名.'
            assert delta not in self.group.arcade_binding_names, '有重复命名.'

        ARCADES_TABLE.set(
            'where hash = %s',
            self.hash,
            subnames=json.dumps(value)
        )

    @property
    def names(self) -> tuple[str, ...]:
        return self.subnames + (self.name, )

    @cached_property
    def num(self) -> Optional[int]:
        result = ARCADES_TABLE.get(
            'where hash = %s',
            self.hash,
            'num'
        )[0]

        return result

    @num.setter
    def num(self, value: Optional[int]):
        ARCADES_TABLE.set(
            'where hash = %s',
            self.hash,
            num=value
        )

    @cached_property
    def update_time(self) -> Optional[datetime.datetime]:
        time = ARCADES_TABLE.get(
            'where hash = %s',
            self.hash,
            'update_time'
        )[0]

        if not time is None:
            time = time.replace(tzinfo=UTC)

        return time

    @update_time.setter
    def update_time(self, value: Optional[datetime.datetime]):
        if not value is None:
            value = value.astimezone(UTC)

        ARCADES_TABLE.set(
            'where hash = %s',
            self.hash,
            update_time=value
        )

    @cached_property
    def update_user(self) -> Optional[User]:
        user = ARCADES_TABLE.get(
            'where hash = %s',
            self.hash,
            'update_user_id'
        )[0]

        if not user is None:
            user = User(int(user))

        return user

    @update_user.setter
    def update_user(self, value: Optional[User]):
        if not value is None:
            value = value.id

        ARCADES_TABLE.set(
            'where hash = %s',
            self.hash,
            update_user_id=value
        )

    @property
    def cabs(self) -> tuple[Cab, ...]:
        return tuple(
            map(
                lambda a: Cab(self.hash, a[0]),
                ARCADES_CABS_TABLE.get_all(
                    'where hash = %s',
                    self.hash,
                    'name'
                )
            )
        )
