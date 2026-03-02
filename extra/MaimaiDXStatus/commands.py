from .MaimaiDXStatusService import MAIMAIDX_STATUS_SERVICE
from abstract.command import COMMAND_GROUP, ask_for_wait
from abstract.message import *
from abstract.session import *


@COMMAND_GROUP.register_command(('maimai', '舞萌状态'), 1)
@ask_for_wait
def maimai(message: MESSAGE, session: Session, args):
    night = at_night()
    match args:
        case []:
            message.reply(ImageMessage(MAIMAIDX_STATUS_SERVICE.render(night)))

        case ['nodes']:
            message.reply(
                TextImageMessage(
                    [
                        f'{node.ID} - {node.NAME}' for node in MAIMAIDX_STATUS_SERVICE.result[1].values()
                    ]
                )
            )

        case [id]:
            node = MAIMAIDX_STATUS_SERVICE.result[1].get(id)
            if node is None:
                message.reply_text(f'没有{id}这个节点.')
                return
            message.reply(ImageMessage(node.stat_render()))

        case final:
            message.reply_text(f'匹配 {final} 失败, 检查输入.')
