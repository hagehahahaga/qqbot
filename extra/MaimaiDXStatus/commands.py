from abstract.bases.importer import operator

from .MaimaiDXStatusService import MAIMAIDX_STATUS_SERVICE
from abstract.command import COMMAND_GROUP
from abstract.message import *
from abstract.session import *
from abstract.bases.text2img import text2img


@COMMAND_GROUP.register_command(('maimai', '舞萌状态'), 1)
def maimai(message: MESSAGE, session: Session, args):
    night = not (8 < local_time().hour < 20)
    match args:
        case []:
            message.reply(ImageMessage(MAIMAIDX_STATUS_SERVICE.render(night)))

        case ['nodes']:
            message.reply(
                ImageMessage(
                    text2img(
                        '\n'.join(
                            map(
                                lambda a: f'{a.ID} - {a.NAME}',
                                MAIMAIDX_STATUS_SERVICE.result[1].values()
                            )
                        )
                    )
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
