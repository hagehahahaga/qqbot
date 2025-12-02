from abstract.bases.importer import time, dispatch, decimal

from config import CONFIG
from abstract.apis.frame_server import FRAME_SERVER
from abstract.apis.table import STOCK_TABLE, USER_TABLE, GROUP_OPTION_TABLE


class User:
    @dispatch
    def __init__(self, data: dict):
        self.id = data['user_id']
        self.name = data['nickname']
        self.role = data.get('role', 'member')
        if self.id in CONFIG.get('operators', []):
            self.role = 'operator'
        if not USER_TABLE.find_exists('id', self.id):
            USER_TABLE.add(f'{self.id}' + ', DEFAULT' * (USER_TABLE.get_len() - 1))
        if not STOCK_TABLE.find_exists('id', self.id):
            STOCK_TABLE.add(f'{self.id}' + ', DEFAULT' * (STOCK_TABLE.get_len() - 1))

    @dispatch
    def __init__(self, id: int):
        self.__init__(FRAME_SERVER.get_stranger_info(id))

    def __str__(self):
        return f'{self.name}({self.id})'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}(user_id: {self.id})> at {hex(id(self))}'

    def get_points(self) -> int:  # 韭菜盒子数操作
        return USER_TABLE.get(f'where id = {self.id}', attr='points')[0]

    def add_points(self, d):
        USER_TABLE.set(
            'id',
            self.id,
            'points',
            USER_TABLE.get(f'where id = {self.id}', attr='points')[0] + decimal.Decimal(d)
        )

    def get_sign_date(self):  # 最后一次签到日期操作
        return USER_TABLE.get(f'where id = {self.id}', attr='sign_date')[0]

    def update_sign_date(self):
        USER_TABLE.set('id', self.id, 'sign_date', time.strftime("%Y-%m-%d"))

    def get_stocks(self):  # 股票数操作
        return STOCK_TABLE.get(f'where id = {self.id}', attr='stocks')[0]

    def add_stocks(self, d):
        STOCK_TABLE.set('id', self.id, 'stocks', self.get_stocks() + d)

    def get_stocks_bought(self):  # 当日购入股票数操作
        return STOCK_TABLE.get(f'where id = {self.id}', attr='stocks_bought')[0]

    def add_stocks_bought(self, d):
        assert d > 0
        STOCK_TABLE.set('id', self.id, 'stocks_bought', self.get_stocks_bought() + d)

    def store_stocks_bought(self):
        self.add_stocks(self.get_stocks_bought())
        STOCK_TABLE.set('id', self.id, 'stocks_bought', 0)

    def get_points_sold(self) -> int:  # 当日收益操作
        return STOCK_TABLE.get(f'where id = {self.id}', attr='points_sold')[0]

    def add_points_sold(self, d):
        STOCK_TABLE.set('id', self.id, 'points_sold', self.get_points_sold() + d)

    def store_points_sold(self):
        self.add_points(self.get_points_sold())
        STOCK_TABLE.set('id', self.id, 'points_sold', 0)

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

    def get_points_sold_using(self):  # 用于撤销/完成交易委托时计算
        return STOCK_TABLE.get(f'where id = {self.id}', attr='points_sold_using')[0]

    def set_points_sold_using(self, num):
        assert num >= 0
        STOCK_TABLE.set('id', self.id, 'points_sold_using', num)

    def add_points_sold_using(self, d):
        STOCK_TABLE.set('id', self.id, 'points_sold_using', self.get_points_sold_using() + d)

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

    def update_trade(self, price, num):
        STOCK_TABLE.set(
            'id', self.id, 'trade_price', price
        ).set(
            'id', self.id, 'trade_num', num
        ).set(
            'id', self.id, 'trade_time',
            f"'{time.strftime('%Y-%m-%d %H:%M:%S')}'"
        )


class Group:
    def __init__(self, id):
        self.id = id
        self.name = FRAME_SERVER.get_group_info(id)['group_name']
        if not GROUP_OPTION_TABLE.find_exists('id', self.id):
            GROUP_OPTION_TABLE.add(str(self.id) + ',default' * (GROUP_OPTION_TABLE.get_len() - 1))

    def __str__(self):
        return f'{self.name}({self.id})'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.name}(group_id: {self.id})> at {hex(id(self))}'
