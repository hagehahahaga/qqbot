import abstract
from abstract.command import COMMAND_GROUP, group_only
from abstract.message import MESSAGE
from abstract.session import Session


@COMMAND_GROUP.register_command(('arcade', '机厅管理'), 1, '管理机厅')
@group_only
def arcade(message: MESSAGE, session: Session, args):
    match args:
        case []:
            return abstract.bot.help(message, session, ['arcade'])
        case ['list']:
            result = message.target.get_arcades()
            if not result:
                message.reply_text('此群还没有设置机厅.')
                return None
            message.reply_text(
                '\n' +
                '\n'.join(
                    f'{name}, '
                    f'别名{data["sub_names"]}, ' +
                    (
                        '未记录人数' if None in data.values() else
                        f'{data["num"]}人({data["update_user"]}记录于{data["update_time"].strftime("%H点%M分 UTC%z")})'
                    )
                    for name, data in result.items()
                )
            )
            return None
        case ['add', name]:
            message.target.add_arcade(name)
        case ['remove', name]:
            message.target.remove_arcade(name)
        case ['option', name, 'add', subname]:
            message.target.add_arcade_subname(name, subname)
        case ['option', name, 'remove', subname]:
            message.target.remove_arcade_subname(name, subname)
        case _:
            message.reply_text(f'匹配 {args} 失败, 检查输入.')
            return None
    message.reply_text('操作成功.')
    arcade(message, session, ['list'])
    return None