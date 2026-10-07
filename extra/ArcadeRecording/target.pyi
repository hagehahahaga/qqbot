from . import Arcade, ArcadeBinding


class User:
    @property
    def arcade_binding_names(self) -> tuple[str, ...]: ...

    @property
    def arcade_bindings(self: User | Group) -> tuple[ArcadeBinding, ...]: ...


class Group:
    @property
    def arcades(self: Group) -> dict[str, Arcade]: ...

    def add_arcade(self: Group, name: str): ...

    def remove_arcade(self: Group, name: str): ...

    @property
    def arcade_names(self: Group) -> tuple[str, ...]: ...

    @property
    def arcade_bindings(self: User | Group) -> tuple[ArcadeBinding, ...]: ...

    @property
    def arcade_binding_names(self) -> tuple[str, ...]: ...
