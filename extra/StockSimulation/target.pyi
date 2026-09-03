from typing import TypedDict, Literal

import datetime


class Commission(TypedDict):
    type: Literal['buy', 'sell']
    price: int
    num: int
    time: datetime.datetime


class Trade(TypedDict):
    price: int
    num: int
    time: datetime.datetime


class User:
    @property
    def stocks(self) -> int: ...

    @stocks.setter
    def stocks(self, value: int): ...

    @property
    def stocks_bought(self) -> int: ...  # 当日购入股票数操作

    @stocks_bought.setter
    def stocks_bought(self, value: int): ...

    def store_stocks_bought(self): ...

    @property
    def points_sold(self) -> int: ...  # 当日收益操作

    @points_sold.setter
    def points_sold(self, value: int): ...

    def store_points_sold(self): ...

    @property
    def commission(self) -> Commission: ...  # 交易委托操作

    def set_commission(self, type: Literal['buy', 'sell'], price: int, num: int): ...

    def reset_commission(self): ...

    def cancel_commission(self): ...

    def achieve_commission(self, price, num): ...

    @property
    def points_sold_using(self) -> int: ...  # 用于撤销/完成交易委托时计算

    @points_sold_using.setter
    def points_sold_using(self, value: int): ...

    @property
    def trade(self) -> Trade: ...  # 最后一次交易时间操作

    def update_trade(self, price: int, num: int): ...
