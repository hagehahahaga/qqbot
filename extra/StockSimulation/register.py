from abstract.target import *

from .tables import STOCK_TABLE

@User.register_func
def get_stocks(self):  # 股票数操作
    return STOCK_TABLE.get(f'where id = {self.id}', attr='stocks')[0]

@User.register_func
def add_stocks(self, d):
    STOCK_TABLE.set('id', self.id, 'stocks', self.get_stocks() + d)

@User.register_func
def get_stocks_bought(self):  # 当日购入股票数操作
    return STOCK_TABLE.get(f'where id = {self.id}', attr='stocks_bought')[0]

@User.register_func
def add_stocks_bought(self, d):
    assert d > 0
    STOCK_TABLE.set('id', self.id, 'stocks_bought', self.get_stocks_bought() + d)

@User.register_func
def store_stocks_bought(self):
    self.add_stocks(self.get_stocks_bought())
    STOCK_TABLE.set('id', self.id, 'stocks_bought', 0)

@User.register_func
def get_points_sold(self) -> int:  # 当日收益操作
    return STOCK_TABLE.get(f'where id = {self.id}', attr='points_sold')[0]

@User.register_func
def add_points_sold(self, d):
    STOCK_TABLE.set('id', self.id, 'points_sold', self.get_points_sold() + d)

@User.register_func
def store_points_sold(self):
    self.add_points(self.get_points_sold())
    STOCK_TABLE.set('id', self.id, 'points_sold', 0)

@User.register_func
def get_commission(self) -> dict:  # 交易委托操作
    result = STOCK_TABLE.get(
        f'where id = {self.id}',
        attr='(commission_type, commission_price, commission_num, commission_time)'
    )
    return {
        'type': result[0],
        'price': result[1],
        'num': result[2],
        'time': result[3],
    }

@User.register_func
def reset_commission(self):
    STOCK_TABLE.set(
        'id', self.id, 'commission_type', 'default'
    ).set(
        'id', self.id, 'commission_price', 'default'
    ).set(
        'id', self.id, 'commission_num', 'default'
    ).set(
        'id', self.id, 'commission_time', 'now()'
    ).set(
        'id', self.id, 'points_sold_using', 'default'
    )

@User.register_func
def set_commission(self, type, price, num):
    assert price >= 0 and num > 0
    match type:
        case 'buy':
            points = price * num
            points_sold = self.get_points_sold()
            delta = points - points_sold
            self.add_points_sold(-points)
            self.add_points_sold_using(points)
            if delta > 0:
                self.add_points(-delta)
                self.add_points_sold(delta)
        case 'sell':
            self.add_stocks(-num)
        case _:
            return

    STOCK_TABLE.set(
        'id', self.id, 'commission_type', f"'{type}'"
    ).set(
        'id', self.id, 'commission_price', price
    ).set(
        'id', self.id, 'commission_num', num
    ).set(
        'id', self.id, 'commission_time',
        f"'{time.strftime('%Y-%m-%d %H:%M:%S')}'"
    )

@User.register_func
def cancel_commission(self):
    commission = self.get_commission()
    match commission['type']:
        case 'buy':
            self.add_points_sold(self.get_points_sold_using())
        case 'sell':
            self.add_stocks(commission['num'])
        case 'none':
            return
    self.reset_commission()

@User.register_func
def achieve_commission(self, price, num):
    commission = self.get_commission()
    result_num = commission['num'] - num
    match commission['type']:
        case 'buy':
            self.add_stocks_bought(num)
            self.add_points_sold_using(-price * num)
        case 'sell':
            self.add_points_sold(num * price)
        case 'none':
            return
    STOCK_TABLE.set('id', self.id, 'commission_num', result_num)
    self.update_trade(price, num)
    if result_num <= 0:
        self.add_points_sold(self.get_points_sold_using())
        self.reset_commission()

@User.register_func
def get_points_sold_using(self):  # 用于撤销/完成交易委托时计算
    return STOCK_TABLE.get(f'where id = {self.id}', attr='points_sold_using')[0]

@User.register_func
def set_points_sold_using(self, num):
    assert num >= 0
    STOCK_TABLE.set('id', self.id, 'points_sold_using', num)

@User.register_func
def add_points_sold_using(self, d):
    STOCK_TABLE.set('id', self.id, 'points_sold_using', self.get_points_sold_using() + d)

@User.register_func
def get_trade(self) -> dict:  # 最后一次交易时间操作
    result = STOCK_TABLE.get(
        f'where id = {self.id}',
        attr='(trade_price, trade_num, trade_time)'
    )
    return {
        'price': result[0],
        'num': result[1],
        'time': result[2],
    }

@User.register_func
def update_trade(self, price, num):
    STOCK_TABLE.set(
        'id', self.id, 'trade_price', price
    ).set(
        'id', self.id, 'trade_num', num
    ).set(
        'id', self.id, 'trade_time',
        f"'{time.strftime('%Y-%m-%d %H:%M:%S')}'"
    )
