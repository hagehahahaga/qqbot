import json
from typing import Literal

from plum import dispatch

from abstract.bases.cached_property import cached_property
from abstract.target import Group, User

from .arcade import Arcade
from .tables import ARCADES_BIND_TABLE


class ArcadeBinding:
    @dispatch
    def __init__(self, target: User | Group, arcade: Arcade):
        self.target = target
        self.arcade = arcade

    @dispatch
    def __init__(self, target: User | Group, name: str):
        self.target = target
        result = ARCADES_BIND_TABLE.get(
            'where (type, id) = (%s, %s) and json_contains(names, json_quote(%s))',
            (self._type, target.id, name),
            'hash'
        )
        assert result, f'{target} 没有 {name} 这个绑定.'
        self.arcade = Arcade(result[0])

    def __str__(self) -> str:
        return  f'{self.target} -> {self.arcade}'

    @property
    def _type(self) -> Literal['group', 'private']:
        return 'group' if isinstance(self.target, Group) else 'private'

    @property
    def exists(self) -> bool:
        return ARCADES_BIND_TABLE.find_exists(
            type=self._type, id=self.target.id, hash=self.arcade.hash
        )
    
    def create(self):
        assert not self.exists, f'Binding {self} already exists.'
        assert self.arcade.exists, f'Arcade {self.arcade} does not exist.'
        ARCADES_BIND_TABLE.add(
            type=self._type, id=self.target.id, hash=self.arcade.hash
        )

    def remove(self):
        assert self.exists, f'Binding {self} does not exist.'
        ARCADES_BIND_TABLE.delete(
            'where (type, id, hash) = (%s, %s, %s)',
            (self._type, self.target.id, self.arcade.hash)
        )

    @cached_property
    def names(self) -> tuple[str, ...]:
        return tuple(
            json.loads(
                ARCADES_BIND_TABLE.get(
                    'where (type, id, hash) = (%s, %s, %s)',
                    (self._type, self.target.id, self.arcade.hash),
                    'names'
                )[0]
            )
        )

    @names.setter
    def names(self, value: tuple[str, ...]):
        assert len(set(value)) == len(value), '有重复命名.'
        deltas = set(value) - set(self.names)
        for delta in deltas:
            if isinstance(self.target, Group):
                assert delta not in self.target.arcade_names, '有重复命名.'
            assert delta not in self.target.arcade_binding_names, '有重复命名.'
            assert delta.isalnum(), f'绑定名 {delta} 不符合要求.'

        ARCADES_BIND_TABLE.set(
            'where (type, id, hash) = (%s, %s, %s)',
            (self._type, self.target.id, self.arcade.hash),
            names=json.dumps(value)
        )