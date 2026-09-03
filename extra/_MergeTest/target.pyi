"""MergeTest 类型存根: 与 register.py 一一对应, 覆盖 hint_merge.py 的合并边界.

注意: 此文件由人工维护(非自动生成), 成员必须与 register.py 中实际注册的成员一致.
成员统一使用 mt_ 前缀, 避免与其他 extra 组件冲突.
"""

import datetime
from typing import Any, TypedDict


class MtData(TypedDict):
    """模块级 TypedDict: 测试 others 顶层块随 extra 依次合并."""
    value: int
    note: str


MT_CONSTANT: int = 42  # 模块级常量: 测试 others 顶层块随 extra 依次合并


class User:
    def mt_echo(self) -> str: ...

    @property
    def mt_counter(self) -> int: ...

    @mt_counter.setter
    def mt_counter(self, value: int): ...

    def mt_shared(self) -> str: ...

    @staticmethod
    def mt_static(value: int) -> int: ...

    @classmethod
    def mt_classmethod(cls, value: int) -> int: ...

    def mt_dotted(self) -> None: ...

    def mt_defaults(self, a: int, b: str = 'x', *args: Any, **kwargs: Any) -> None: ...

    async def mt_async(self) -> str: ...


class Group:
    def mt_shared(self) -> str: ...

    def mt_group_only(self) -> None: ...
