import abstract
from abstract.bot import BOT
from abstract.command import COMMAND_GROUP, group_only
from abstract.message import MESSAGE, GroupMessage, TextMessage, NodeMessage
from abstract.session import Session
from abstract.target import User
from extra.ArcadeRecording import ARCADES_BIND_TABLE


@COMMAND_GROUP.register_command(('arcade', '机厅管理'), 1, '管理机厅')
def arcade(message: MESSAGE, session: Session, args):
    target = message.target if isinstance(message, GroupMessage) else message.sender

    match args:
        case ['binding', 'list']:
            binding_arcades = target.get_binding_arcades()
            if not binding_arcades:
                message.reply_text('没有绑定机厅.')
                return
            message.reply(
                [
                    NodeMessage(
                        User(BOT.id),
                        [TextMessage(text)]
                    ) for text in ['已绑定以下机厅'] + [
                        f'{name} 来自 {data["group"]}({data["hash"].hex()})' for name, data in
                        binding_arcades.items()
                    ]
                ]
            )
            return

        case ['binding', hash, 'add', subname]:
            hash = bytes.fromhex(hash)
            target.add_arcade_binding_name(hash, subname)

        case ['binding', hash, 'remove', subname]:
            hash = bytes.fromhex(hash)
            target.remove_arcade_binding_name(hash, subname)

        case ['bind', hash]:
            hash = bytes.fromhex(hash)

            target.bind_arcade(hash)

        case ['unbind', hash]:
            try:
                hash = bytes.fromhex(hash)
            except ValueError:
                arcades = target.get_arcade_bindings(hash)
                if not arcades:
                    message.reply_text(f'没有绑定 {hash} 这个机厅.')
                if len(arcades) == 1:
                    names, data = next(
                        iter(
                            arcades.items()
                        )
                    )
                    target.unbind_arcade(
                        data['hash']
                    )
                    message.reply_text(f'已解绑群聊{data["group"]}的机厅{names}.')
                    return

                message.reply(
                    [
                        NodeMessage(
                            User(BOT.id),
                            [TextMessage(text)]
                        ) for text in [
                            '你想解绑的机厅有几个匹配结果.',
                            '以下是他们的信息, 检查后将指令中机厅名改成对应hash来解绑.'
                        ] + [
                            f'{name} 来自 {data["group"]}({data["hash"].hex()})'
                            f'\n绑定名: {ARCADES_BIND_TABLE.get("where ",attr="names")}' for name, data in arcades.items()
                        ]
                    ]
                )
                return

            target.unbind_arcade(hash)

        case _:
            arcade_group(message, session, args)
            return
    message.reply_text('操作成功.')

@group_only
def arcade_group(message: MESSAGE, session: Session, args):
    match args:
        case []:
            abstract.bot.help(message, session, ['arcade'])
        case ['list']:
            result = message.target.get_arcades()
            if not result:
                message.reply_text('此群还没有设置机厅.')
                return
            message.reply_text(
                '\n' +
                '\n'.join(
                    f'{name}, '
                    f'别名{data["subnames"]}, ' +
                    (
                        '未记录人数' if None in data.values() else
                        f'{data["num"]}人({data["update_user"]}记录于{data["update_time"].strftime("%H点%M分 UTC%z")})'
                    )
                    for name, data in result.items()
                )
            )
            return
        case ['add', name]:
            message.target.add_arcade(name)
        case ['remove', name]:
            message.target.remove_arcade(name)
        case ['option', name, 'add', subname]:
            message.target.add_arcade_subname(name, subname)
        case ['option', name, 'remove', subname]:
            message.target.remove_arcade_subname(name, subname)
        case ['hash', name]:
            message.reply_text(message.target.get_arcade_hash(name).hex())
            return
        case _:
            message.reply_text(f'匹配 {args} 失败, 检查输入.')
            return
    message.reply_text('操作成功.')
    arcade_group(message, session, ['list'])