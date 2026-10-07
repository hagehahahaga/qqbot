import operator, itertools

from abstract.target import *

from .arcade import Arcade
from .arcade_binding import ArcadeBinding
from .tables import ARCADES_TABLE, ARCADES_BIND_TABLE, ARCADES_CABS_TABLE


@Group.register_attr
@property
def arcades(self: Group) -> dict[str, Arcade]:
    result = ARCADES_TABLE.get_all(
        'where group_id = %s', self.id, 'hash', )
    response = {}
    for hash, in result:
        arcade = Arcade(hash)
        response[arcade.name] = arcade

    return response


@Group.register_attr
def add_arcade(self: Group, name: str):
    """
    向群组添加一个新的机厅

    功能说明：
    - 验证 name 是否仅由字母和数字组成
    - 检查 name 是否与本群已有机厅名称或绑定名称重复
    - 在 arcades 表中插入新记录, hash 由数据库生成列自动计算

    :param name: 机厅名称
    :raises AssertionError: name格式不符合要求，或名称重复
    """
    assert name.isalnum(), '机厅名不符合要求.'
    assert name not in self.arcade_names, '有重复命名.'
    assert name not in self.arcade_binding_names, '有重复命名.'
    with ARCADES_TABLE as cursor:
        cursor.execute(
            f'insert into {cursor.table_name} (group_id, name) '
            f'values (%s, %s)',
            (self.id, name)
        )


@Group.register_attr
def remove_arcade(self: Group, name: str):
    """
    从群组中移除一个机厅

    功能说明：
    - 不允许使用别名（subname）作为参数移除，只能使用主名称
    - 要求机厅没有别名（subnames为空），需要先移除所有别名
    - 依次删除该机厅在 arcades_bind、arcades_cabs 表中的关联记录, 最后删除 arcades 表中的记录
    - 删除机厅会连带清空该机厅的机台与全部绑定

    :param name: 机厅主名称（不能使用别名）
    :raises AssertionError: 使用了别名、机厅不存在、或机厅还有未移除的别名
    """

    arcade = Arcade(self, name)
    assert name not in arcade.subnames, '安全起见移除不能使用机厅别名.'
    assert not arcade.subnames, '安全起见移除机厅需要先移除机厅所有别名.'
    ARCADES_BIND_TABLE.delete('where hash = %s', arcade.hash)
    ARCADES_CABS_TABLE.delete('where hash = %s', arcade.hash)
    ARCADES_TABLE.delete('where (group_id, name) = (%s, %s)', (self.id, name))


@Group.register_attr
@property
def arcade_names(self: Group) -> tuple[str, ...]:
    """
    获取群组所有机厅的名称和别名列表

    功能说明：
    - 取本群全部机厅(Group.arcades), 逐个读取其 names(主名称 + 所有别名)
    - 将所有 names 展开合并为一个扁平元组

    :return: 群组内所有机厅名称和别名的完整元组
    """
    return tuple(
        itertools.chain(
            *map(
                operator.attrgetter('names'),
                self.arcades.values()
            )
        )
    )


@Group.register_attr
@User.register_attr
@property
def arcade_bindings(self: User | Group) -> tuple[ArcadeBinding, ...]:
    if isinstance(self, Group):
        type = 'group'
    else:
        type = 'private'

    return tuple(
        map(
            lambda a: ArcadeBinding(self, Arcade(a[0])),
            ARCADES_BIND_TABLE.get_all(
                'where (type, id) = (%s, %s)',
                (type, self.id),
                'hash'
            )
        )
    )


@Group.register_attr
@User.register_attr
@property
def arcade_binding_names(self: User | Group) -> tuple[str, ...]:
    """
    获取当前用户或群组所有已绑定机厅的自定义名称列表

    功能说明：
    - 取当前用户或群组的全部绑定(arcade_bindings), 逐个读取其 names(自定义名称)
    - 将所有 names 展开合并为一个扁平元组

    :return: 所有绑定自定义名称的完整元组
    """
    return tuple(
        itertools.chain(
            *map(
                operator.attrgetter('names'),
                self.arcade_bindings
            )
        )
    )
