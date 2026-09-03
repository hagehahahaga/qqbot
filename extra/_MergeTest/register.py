"""MergeTest 组件: 用于测试 extra/hint_merge.py 的边界条件.

覆盖的边界场景:
1. 同一函数同时注册到多个类(@Group.register_attr + @User.register_attr 装饰器叠加)
2. property getter/setter 同名注册(hint_merge 中 set 天然去重)
3. 类名别名导入(from abstract.target import User as U)
4. 完整限定名装饰器(@abstract.target.User.register_attr, 不依赖别名)
5. @staticmethod / @classmethod 注册(描述符对象携带 __name__)
6. async 方法(AsyncFunctionDef)与带默认值/可变参数的方法
7. 普通方法注册

注意: 成员统一使用 mt_ 前缀, 避免与 ArcadeRecording / StockSimulation 冲突,
使 hint_merge 的跨组件冲突检查保持通过.

注: 本文件仅被 hint_merge.py 静态解析(AST), 不会由 bot 加载执行.
"""

import abstract.target
from typing import Any

from abstract.target import Group
from abstract.target import User as U


# --- 1. 普通方法, 通过别名导入注册 ---

@U.register_attr
def mt_echo(self) -> str:
    return 'mt'


# --- 2. property: getter/setter 同名, setter 携带注册装饰器 ---

@property
def mt_counter(self) -> int:
    return getattr(self, '_mt_counter', 0)


@U.register_attr
@mt_counter.setter
def mt_counter(self, value: int):
    self._mt_counter = value


# --- 3. 同一函数同时注册到 User 与 Group(装饰器叠加) ---

@Group.register_attr
@U.register_attr
def mt_shared(self) -> str:
    return 'shared'


# --- 4. @staticmethod 注册(staticmethod 对象携带 __name__) ---

@U.register_attr
@staticmethod
def mt_static(value: int) -> int:
    return value * 2


# --- 5. @classmethod 注册 ---

@U.register_attr
@classmethod
def mt_classmethod(cls, value: int) -> int:
    return value + 1


# --- 6. 完整限定名装饰器, 不依赖别名 ---

@abstract.target.User.register_attr
def mt_dotted(self) -> None:
    ...


# --- 7. 带默认值/可变参数的方法 ---

@U.register_attr
def mt_defaults(self, a: int, b: str = 'x', *args: Any, **kwargs: Any) -> None:
    ...


# --- 8. async 方法 ---

@U.register_attr
async def mt_async(self) -> str:
    return 'async'


# --- 9. 仅注册到 Group 的方法 ---

@Group.register_attr
def mt_group_only(self) -> None:
    ...
