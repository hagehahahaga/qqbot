from abstract.bases.cached_property import cached_property

from .tables import ARCADES_CABS_TABLE


class Cab:
    def __init__(self, arcade_hash: bytes, name: str):
        self.arcade_hash = arcade_hash
        self.name = name

    @property
    def exists(self) -> bool:
        return ARCADES_CABS_TABLE.find_exists(
            hash=self.arcade_hash, name=self.name
        )

    def create(self):
        assert self.name.isalnum(), '机台名不符合要求.'
        assert not self.exists, f'Cab {self.name} already exists'
        ARCADES_CABS_TABLE.add(
            hash=self.arcade_hash, name=self.name
        )

    def remove(self):
        assert self.exists, f'Cab {self.name} does not exist'
        ARCADES_CABS_TABLE.delete(
            'where (hash, name) = (%s, %s)',
            (self.arcade_hash, self.name)
        )

    @cached_property
    def slot(self) -> int:
        return ARCADES_CABS_TABLE.get(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            'slot'
        )[0]

    @slot.setter
    def slot(self, value: int):
        ARCADES_CABS_TABLE.set(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            slot=value
        )

    @cached_property
    def tracks(self) -> int:
        return ARCADES_CABS_TABLE.get(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            'tracks'
        )[0]

    @tracks.setter
    def tracks(self, value: int):
        ARCADES_CABS_TABLE.set(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            tracks=value
        )

    @cached_property
    def must_pickup(self) -> bool:
        return bool(
            ARCADES_CABS_TABLE.get(
                'where hash = %s and name = %s',
                (self.arcade_hash, self.name),
                'must_pickup'
            )[0]
        )

    @must_pickup.setter
    def must_pickup(self, value: bool):
        ARCADES_CABS_TABLE.set(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            must_pickup=value
        )

    @cached_property
    def pickup_bonus(self) -> bool:
        return bool(
            ARCADES_CABS_TABLE.get(
                'where hash = %s and name = %s',
                (self.arcade_hash, self.name),
                'pickup_bonus'
            )[0]
        )

    @pickup_bonus.setter
    def pickup_bonus(self, value: bool):
        ARCADES_CABS_TABLE.set(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            pickup_bonus=value
        )

    @cached_property
    def num(self) -> int:
        return ARCADES_CABS_TABLE.get(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            'num'
        )[0]

    @num.setter
    def num(self, value: int):
        ARCADES_CABS_TABLE.set(
            'where hash = %s and name = %s',
            (self.arcade_hash, self.name),
            num=value
        )
