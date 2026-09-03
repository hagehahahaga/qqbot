import time

import abstract
from abstract.bot import BOT
from abstract.command import COMMAND_GROUP
from abstract.message import MESSAGE
from abstract.session import Session
from abstract.target import User

from .tables import STOCK_TABLE


@COMMAND_GROUP.register_command(('stock', '股票'), 1, '股票系统')
def stock(message: MESSAGE, session: Session, args):
    date = time.strftime('%Y-%m-%d')
    commission = message.sender.commission
    trade = message.sender.trade
    STOCK_TABLE.set(
        'id', BOT.id, 'commission_time', f"'{time.strftime('%Y-%m-%d %H:%M:%S')}'"
    )
    if str(commission['time']).split(' ')[0] < date and commission['type'] != 'none':
        message.sender.cancel_commission()
        message.reply_text('过期交易委托已取消!')
    if str(trade['time']).split(' ')[0] < date:
        message.reply_text(
            '\n昨日收益:\n'
            f'  韭菜盒子收入: {message.sender.points_sold}'
            f'  股票收入: {message.sender.stocks_bought}'
        )
        message.sender.store_points_sold()
        message.sender.store_stocks_bought()
        message.sender.update_trade(0, 0)

    match args:
        case []:
            return abstract.bot.help(message, session, ['stock'])
        case ['status', *args]:
            match args:
                case []:
                    message.reply_text(
                        '\n当前状态:\n'
                        f'  持有股票: {message.sender.stocks}\n'
                        f'  今日股票购入: {message.sender.stocks_bought}\n'
                        f'  今日收益: {message.sender.points_sold}\n'
                        f'  最后一次交易时间: {trade["time"]}\n'
                        f'  最后一次交易价格: {trade["price"]}\n'
                        f'  最后一次交易数量: {trade["num"]}'
                    )
                case ['stock']:
                    trade = User(STOCK_TABLE.get('ORDER BY trade_time desc', attr='id')[0]).trade
                    message.reply_text(
                        '\n当前股市状态:\n'
                        f'  最后一次交易价格: {trade["price"]}\n'
                    )
                case ['commission']:
                    commission = message.sender.commission
                    if commission['type'] == 'none':
                        message.reply_text('当前没有交易委托中')
                        return
                    message.reply_text(
                        '\n当前交易委托:\n'
                        f'  类型: {commission["type"]}\n'
                        f'  价格: {commission["price"]}\n'
                        f'  数量: {commission["num"]}'
                        f'  时间: {commission["time"]}\n'
                    )
                case [final]:
                    message.reply_text(f'{final} 不是可以查询的数据!')
                case final:
                    message.reply_text(f'匹配 {final} 失败, 检查输入.')
            return

        case [action, price, num] if action in ('buy', 'sell'):
            if commission['type'] != 'none':
                message.reply_text('你现在仍有一个交易委托进行中!')
                return
            try:
                price = int(price)
                num = int(num)
            except ValueError:
                message.reply_text('输入的参数无法转换为数字!')
                return

        case ['cancel']:
            message.sender.cancel_commission()
            message.reply_text('已有的交易委托已撤销.')
            return
        case final:
            message.reply_text(f'匹配 {final} 失败, 检查输入.')
            return

    match action:
        case 'buy':
            if price * num > message.sender.points + message.sender.points_sold:
                message.reply_text('流动资金不足!')
                return
        case 'sell':
            if num > message.sender.stocks:
                message.reply_text('可卖出股票不足!')
                return

    message.sender.set_commission(action, price, num)
    while target_id := STOCK_TABLE.get(
            f"where (commission_type, date(commission_time)) = ('{'sell' if action == 'buy' else 'buy'}', curdate())"
            f"and commission_price {'<=' if action == 'buy' else '>'} {price}",
            f"order by commission_price {'asc' if action == 'buy' else 'desc'}, commission_time asc",
            attr='id'
    )[0]:
        target = User(target_id)
        target_commission = target.commission
        if num < target_commission['num']:
            deal_num = num
        else:
            deal_num = target_commission['num']

        num -= deal_num
        message.sender.achieve_commission(target_commission['price'], deal_num)
        message.reply_text(f' 你以 {target_commission["price"]}韭菜盒子/股 的价格 {action} 了 {deal_num}股.')
        target.achieve_commission(target_commission['price'], deal_num)
        if not num:
            break
    else:
        message.reply_text(f'交易还剩 {num}股 未完成, 交易委托中...')
