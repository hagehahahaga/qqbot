from abstract.bot import BOT, help
from abstract.command import COMMAND_GROUP, group_only
from abstract.message import MESSAGE, GroupMessage, TextPart, NodePart
from abstract.session import Session
from abstract.target import User

from .arcade import Arcade
from .arcade_binding import ArcadeBinding
from .cab import Cab


@COMMAND_GROUP.register_command(('arcade', '机厅管理'), 1, '管理机厅')
def arcade(message: MESSAGE, session: Session, args):
    if isinstance(message, GroupMessage):
        assert message.sender.role != 'member', '管理群聊机厅需要管理员及以上权限.'
    target = message.target if isinstance(message, GroupMessage) else message.sender

    match args:
        case []:
            help(message, session, ['arcade'])
        case ['bind', hash]:
            hash = bytes.fromhex(hash)
            arcade = Arcade(hash)
            ArcadeBinding(target, arcade).create()
            message.reply_text(f'已绑定 {arcade}.')

        case ['unbind', hash]:
            try:
                hash = bytes.fromhex(hash)
            except ValueError:
                hash: str
                binding = ArcadeBinding(target, hash)
            else:
                binding = ArcadeBinding(target, Arcade(hash))

            binding.remove()

            message.reply_text(f'已解绑 {binding.arcade}.')

        case ['binding']:
            bindings: tuple[ArcadeBinding, ...] = target.arcade_bindings
            if not bindings:
                message.reply_text('没有绑定机厅.')
                return
            message.reply(
                [
                    NodePart(
                        User(BOT.id),
                        [TextPart(text)]
                    ) for text in ['已绑定以下机厅'] + [
                        (
                            f'{binding.names}' if binding.names else
                            '未设置别名'
                        ) +
                        (
                            ' 未记录人数' if binding.arcade.num is None else
                            f' {binding.arcade.num}人({binding.arcade.update_user} 记录于 {binding.arcade.update_time.strftime("%H点%M分 UTC%z")}) '
                        ) +
                        f' 来自 {binding.arcade.group}({binding.arcade.hash.hex()})' for binding in
                        bindings
                    ]
                ]
            )

        case ['binding', hash, 'subname', 'add', *subnames]:
            hash = bytes.fromhex(hash)
            arcade = Arcade(hash)
            binding = ArcadeBinding(target, arcade)
            assert binding.exists, f'绑定 {binding} 不存在.'
            binding.names += tuple(subnames)
            message.reply_text(f'已添加别名 {" ".join(subnames)} 给{arcade}.')

        case ['binding', hash, 'subname', 'remove', *subnames]:
            hash = bytes.fromhex(hash)
            arcade = Arcade(hash)
            binding = ArcadeBinding(target, arcade)
            assert binding.exists, f'绑定 {binding} 不存在.'
            exception = set(subnames) - set(binding.names)
            assert not exception, f'{" ".join(exception)} 不是 {arcade} 的别名.'
            binding.names = tuple(set(binding.names) - set(subnames))
            message.reply_text(f'已移除 {arcade} 的别名 {" ".join(subnames)}.')

        case _:
            if isinstance(message, GroupMessage):
                arcade_group(message, session, args)
                return
            message.reply_text(f'匹配 {args} 失败, 检查输入.')

@group_only
def arcade_group(message: GroupMessage, session: Session, args):
    match args:
        case ['list']:
            arcades = message.target.arcades
            if not arcades:
                message.reply_text('此群还没有设置机厅.')
                return
            message.reply_text(
                '\n' +
                '\n'.join(
                    f'{arcade}, ' +
                    (f'别名 {" ".join(arcade.subnames)}, ' if arcade.subnames else '无别名, ') +
                    (
                        '未记录人数' if arcade.num is None else
                        f'{arcade.num}人({arcade.update_user} 记录于 {arcade.update_time.strftime("%H点%M分 UTC%z")}) '
                    )
                    for name, arcade in arcades.items()
                )
            )
            return
        case ['add', name]:
            message.target.add_arcade(name)
        case ['remove', name]:
            message.target.remove_arcade(name)
        case [name, 'subname', 'add', *subnames]:
            Arcade(message.target, name).subnames += tuple(subnames)
        case [name, 'subname', 'remove', *subnames]:
            arcade = Arcade(message.target, name)
            exception = set(subnames) - set(arcade.subnames)
            assert not exception, f'{" ".join(exception)} 不是 {arcade} 的别名.'
            arcade.subnames = tuple(set(arcade.subnames) - set(subnames))
        case [name, 'cab']:
            arcade = Arcade(message.target, name)
            cabs = arcade.cabs
            message.reply_text(
                f'{arcade} 记录了以下机台:\n' +
                '\n'.join(
                    f'{cab.name}({cab.slot}个上机位)' for cab in cabs
                )
            )
            return
        case [name, 'cab', 'add', cabname]:
            Cab(Arcade(message.target, name).hash, cabname).create()
        case [name, 'cab', 'remove', cabname]:
            Cab(Arcade(message.target, name).hash, cabname).remove()
        case [name, 'cab', cabname, 'slot', num]:
            assert num.isdecimal(), f'{num}好像不是一个数字?'
            num = int(num)
            assert num != 0, '机位数不能设置为棍母.'
            assert num > 0, '负数个是机厅倒欠吗.'
            assert num < 256, '根本没有这么多机位的机厅.'

            cab = Cab(Arcade(message.target, name).hash, cabname)
            assert cab.exists, f'不存在机台{cab.name}'
            cab.slot = num
        case [name, 'cab', cabname, 'slot']:
            arcade = Arcade(message.target, name)
            cab = Cab(arcade.hash, cabname)
            assert cab.exists, f'未记录机台{cab.name}'
            message.reply_text(f'{arcade}的{cab.name}有{cab.slot}个上机位')
            return
        case [name, 'cab', cabname, 'pickupbonus', pickupbonus]:
            assert pickupbonus in ('0', '1'), f'请填入0或1, 而不是{pickupbonus}'
            pickupbonus = bool(int(pickupbonus))
            arcade = Arcade(message.target, name)
            cab = Cab(arcade.hash, cabname)
            assert cab.exists, f'未记录机台{cab.name}'

            cab.pickup_bonus = pickupbonus
        case [name, 'cab', cabname, 'pickupbonus']:
            arcade = Arcade(message.target, name)
            cab = Cab(arcade.hash, cabname)
            assert cab.exists, f'未记录机台{cab.name}'
            message.reply_text(f'机台{cab.name}的拼机加1track设置为{cab.pickup_bonus}')
            return
        case [name, 'cab', cabname, 'mustpickup', mustpickup]:
            assert mustpickup in ('0', '1'), f'请填入0或1, 而不是{mustpickup}'
            mustpickup = bool(int(mustpickup))
            arcade = Arcade(message.target, name)
            cab = Cab(arcade.hash, cabname)
            assert cab.exists, f'未记录机台{cab.name}'

            cab.must_pickup = mustpickup
        case [name, 'cab', cabname, 'mustpickup']:
            arcade = Arcade(message.target, name)
            cab = Cab(arcade.hash, cabname)
            assert cab.exists, f'未记录机台{cab.name}'
            message.reply_text(f'机台{cab.name}的必须拼机设置为{cab.must_pickup}')
            return
        case [name, 'hash']:
            message.reply_text(Arcade(message.target, name).hash.hex())
            return
        case _:
            message.reply_text(f'匹配 {args} 失败, 检查输入.')
            return
    message.reply_text('操作成功.')
