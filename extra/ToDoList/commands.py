from abstract.command import COMMAND_GROUP
from abstract.message import MESSAGE, TextMessage, AtMessage
from abstract.session import Session

from .tables import TODOLIST_TABLE


@COMMAND_GROUP.register_command(('todo', '待办', '待办事项'), 1, '待办事项操作')
def todo(message: MESSAGE, session: Session, args):
    match args:
        case []:
            todo(message, session, ['list'])
        case ['add', text]:
            assert not TODOLIST_TABLE.find_exists('(user_id, do)', (message.sender.id, text)), f'你已设置 {text} 这个待办.'
            TODOLIST_TABLE.add(f'{message.sender.id}, "{text}", DEFAULT')
            message.reply_text(f'待办{text}已添加.')
        case ['remove', text]:
            assert TODOLIST_TABLE.find_exists('(user_id, do)', (message.sender.id, text)), f'你并没有设置 {text} 这个待办.'
            if TODOLIST_TABLE.get(f'where user_id = {message.sender.id} and do = "{text}"', attr='finished')[0]:
                TODOLIST_TABLE.delete('(user_id, do)', (message.sender.id, text))
                message.reply_text(f'已删除待办 {text}.')
                return

            message.reply_text('这个待办尚未完成, 确定放弃? 发送"Y"来放弃.')
            response = session.pipe_get(message)
            response_text = response.get_parts_by_type(TextMessage)
            if not response_text:
                response.reply_text('待办未放弃.')
                return
            response_text = response_text[0].text
            if response_text.upper() != 'Y':
                response.reply_text('待办未放弃.')
                return

            TODOLIST_TABLE.delete('(user_id, do)', (message.sender.id, text))
            response.reply_text(f'已删除待办 {text}.')

        case ['list', *all]:
            results = TODOLIST_TABLE.get_all(f'where user_id = {message.sender.id}', attr='do, finished')
            if not all or all[0] != 'all':
                results = list(filter(lambda a: not a[1], results))
            if not results:
                message.reply_text('没有待办事项记录' if all else '没有待办事项')
                return
            message.reply_text(
                '\n' +
                '\n'.join(f'{result[0]} - {"已完成" if result[1] else "未完成"}' for result in results)
            )

        case ['finish', text]:
            assert TODOLIST_TABLE.find_exists('(user_id, do)', (message.sender.id, text)), f'你并没有设置 {text} 这个待办.'
            assert TODOLIST_TABLE.find_exists('(user_id, do, finished)', (message.sender.id, text, False)), f'{text} 这个待办已经完成了.'
            with TODOLIST_TABLE:
                TODOLIST_TABLE.cursor.execute(
                    f"UPDATE {TODOLIST_TABLE.name} SET `finished` = 1 WHERE (`user_id`, `do`) = (%s, %s)",
                    (message.sender.id, text)
                )
            message.reply_text(
                f'今天是著名大神{message.sender.name} {text} 的日子。'
                f'生活中的酸甜苦辣，记录着命运的轨迹，轨迹留下你的影子，{text} 之际，送给你的祝愿最诚挚，衷心祝你大吉大利，顺心如意。'
                f'只有尊重自己的人，才能够更勇于缩小自己，通过退让来成全别人，非愚即智。'
                f'梦自己想梦的，做自己想做的，因为生命只有一次，机会不会再来。'
                f'人生苦短，咱们何必计较得失，有爱就有梦。每个人都有一番不一样的经历，每个人都是一部新鲜的故事。'
                f'懂得珍惜，风雨兼程的日子，有他有我也有你。'
            )
        case final:
            message.reply_text(f'匹配 {final} 失败, 检查输入.')
