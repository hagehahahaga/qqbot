import time
from datetime import UTC
from typing import Literal

from abstract.bases.importer import local_time
from abstract.target import User

from .tables import STOCK_TABLE


@property
def stocks(self) -> int:
    return int(STOCK_TABLE.get(f'where id = {self.id}', attr='stocks')[0])


@User.register_attr
@stocks.setter
def stocks(self, value: int):
    STOCK_TABLE.set('id', self.id, 'stocks', value)


@property
def stocks_bought(self) -> int:  # 当日购入股票数操作
    return int(STOCK_TABLE.get(f'where id = {self.id}', attr='stocks_bought')[0])


@User.register_attr
@stocks_bought.setter
def stocks_bought(self, value: int):
    STOCK_TABLE.set('id', self.id, 'stocks_bought', value)


@User.register_attr
def store_stocks_bought(self):
    self.stocks += self.stocks_bought
    self.stocks_bought = 0


@property
def points_sold(self) -> int:  # 当日收益操作
    return STOCK_TABLE.get(f'where id = {self.id}', attr='points_sold')[0]


@User.register_attr
@points_sold.setter
def points_sold(self, value: int):
    STOCK_TABLE.set('id', self.id, 'points_sold', value)


@User.register_attr
def store_points_sold(self):
    self.points += self.points_sold
    self.points_sold = 0


@User.register_attr
@property
def commission(self) -> dict:  # 交易委托操作
    result = STOCK_TABLE.get(
        f'where id = {self.id}', attr='(commission_type, commission_price, commission_num, commission_time)', )
    return {
        'type': result[0], 'price': result[1], 'num': result[2], 'time': result[3],
    }


@User.register_attr
def set_commission(self, type: Literal['buy', 'sell'], price: int, num: int):
    assert price >= 0 and num > 0
    match type:
        case 'buy':
            total = price * num
            delta = total - self.points_sold
            self.points_sold -= total
            self.points_sold_using += total
            if delta > 0:
                self.points -= delta
                self.points_sold += delta
        case 'sell':
            self.stocks -= num
        case others:
            raise ValueError(f'Unknown commission type: {others}.')

    STOCK_TABLE.set(
        'id', self.id, 'commission_type', f"'{type}'", ).set(
        'id', self.id, 'commission_price', price, ).set(
        'id', self.id, 'commission_num', num, ).set(
        'id', self.id, 'commission_time', local_time().astimezone(UTC))


@User.register_attr
def reset_commission(self):
    STOCK_TABLE.set(
        'id', self.id, 'commission_type', 'default', ).set(
        'id', self.id, 'commission_price', 'default', ).set(
        'id', self.id, 'commission_num', 'default', ).set(
        'id', self.id, 'commission_time', local_time().astimezone(UTC), ).set(
        'id', self.id, 'points_sold_using', 'default', )


@User.register_attr
def cancel_commission(self):
    commission = self.commission
    match commission['type']:
        case 'buy':
            self.points_sold += self.points_sold_using
        case 'sell':
            self.stocks += commission['num']
        case 'none':
            return
    self.reset_commission()


@User.register_attr
def achieve_commission(self, price, num):
    commission = self.commission
    result_num = commission['num'] - num
    match commission['type']:
        case 'buy':
            self.stocks_bought += num
            self.points_sold_using -= price * num
        case 'sell':
            self.points_sold += num * price
        case 'none':
            return
    STOCK_TABLE.set('id', self.id, 'commission_num', result_num)
    self.update_trade(price, num)
    if result_num <= 0:
        self.points_sold += self.points_sold_using
        self.reset_commission()


@property
def points_sold_using(self) -> int:  # 用于撤销/完成交易委托时计算
    return STOCK_TABLE.get(f'where id = {self.id}', attr='points_sold_using')[0]


@User.register_attr
@points_sold_using.setter
def points_sold_using(self, value: int):
    assert value >= 0
    STOCK_TABLE.set('id', self.id, 'points_sold_using', value)


@User.register_attr
@property
def trade(self) -> dict:  # 最后一次交易时间操作
    result = STOCK_TABLE.get(
        f'where id = {self.id}', attr='(trade_price, trade_num, trade_time)', )
    return {
        'price': int(result[0]), 'num': int(result[1]), 'time': result[2],
    }


@User.register_attr
def update_trade(self, price: int, num: int):
    STOCK_TABLE.set(
        'id', self.id, 'trade_price', price, ).set(
        'id', self.id, 'trade_num', num, ).set(
        'id', self.id, 'trade_time', f"'{time.strftime('%Y-%m-%d %H:%M:%S')}'", )
