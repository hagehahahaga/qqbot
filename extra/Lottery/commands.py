import time, persistedstate, pathlib, random

from abstract.command import COMMAND_GROUP
from abstract.message import MESSAGE
from abstract.session import Session

@COMMAND_GROUP.register_command(('lottery', '彩票', '抽奖'), info='5个韭菜盒子购买一个韭菜盒子彩票')
def lottery(message: MESSAGE, session: Session):
    assert data.time > time.time(), '彩票店接盘侠还未赶来...'

    match random.randint(1, 100):
        case score if score <= 1:
            message.reply_text(f'恐怖! 特大奖来袭! 奖池清空, +{data.pool - 5}. 无语, 典型的特大男人思维.')
            message.sender.points += data.pool - 5
            data.pool = 20
        case score if score <= 10:
            message.reply_text('大奖. +15')
            message.sender.points += 15
            data.pool -= 15
        case score if score <= 20:
            message.reply_text('小奖. +5')
            message.sender.points += 5
            data.pool -= 5
        case score if score <= 50:
            message.reply_text('不亏. +0')
        case _:
            message.sender.points -= 5
            data.pool += 5
            message.reply_text('未中奖...')

    if data.pool < 0:
        data.time = time.time() + 5 * 60
        data.pool = 0
        message.reply_text('彩票店破产跑路了! 接盘侠预计在 5 分钟后赶来.')
        return
    message.reply_text(f'当前奖池: {data.pool}个.')

file = pathlib.Path(__file__).parent / 'data.yaml'
if not file.exists():
    data = persistedstate.PersistedState(file, pool=0, time=0)
else:
    data = persistedstate.PersistedState(file)