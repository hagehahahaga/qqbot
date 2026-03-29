from abstract.bases.exceptions import CommandCancel
from abstract.command import COMMAND_GROUP, cost, ask_for_wait
from abstract.message import MESSAGE, RecordMessage, TextMessage
from abstract.session import Session

from .speaker import SPEAKER_MANAGER


@COMMAND_GROUP.register_command(('tts', 'ai语音'), 1, 'ai语音')
@cost(2)
@ask_for_wait
def TTS(message: MESSAGE, session: Session, args):
    match args:
        case [speaker, *text]:
            text = ' '.join(text)
        case final:
            message.reply_text(f'匹配{final}失败, 检查输入.')
            return

    message.reply(
        RecordMessage(SPEAKER_MANAGER[speaker].TTS(text))
    )


@COMMAND_GROUP.register_command(
    ('svc', 'ai变音', '变音', '变声'),
    {'needed_type': RecordMessage, 'needed_num': 1},
    'ai变音'
)
@cost(2)
@ask_for_wait
def SVC(message: MESSAGE, session: Session, args: list[RecordMessage]):
    try:
        command_args = message.get_parts_by_type(TextMessage)[0].to_args()
        speaker = command_args[1]
        try:
            pitch = float(command_args[2])
        except IndexError:
            pitch = None
    except IndexError:
        raise CommandCancel('未指定speaker.')

    message.reply(
        RecordMessage(
            SPEAKER_MANAGER[speaker].SVC(args[0].record, pitch)
        )
    )
