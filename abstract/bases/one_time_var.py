class OneTimeVar:
    def __init__(self, initial_value=None):
        self._value = initial_value  # 存储变量值
        self._updated = False        # 标记是否已修改过（初始值不算修改）

    @property
    def value(self):
        """获取当前值"""
        return self._value

    @value.setter
    def value(self, new_value):
        """设置新值，仅允许一次修改"""
        if self._updated:
            # 已修改过，抛出异常
            raise RuntimeError("变量只能修改一次")
        # 第一次修改：更新值并标记为已修改
        self._value = new_value
        self._updated = True

    def __repr__(self):
        """打印时显示值（类似普通变量）"""
        return repr(self._value)

    def __eq__(self, other):
        """支持和普通值比较（如 a == 1）"""
        return self._value == other

    def __hash__(self):
        """支持作为字典键等场景"""
        return hash(self._value)

    # 可选：添加类型转换方法，让它更像普通类型
    def __int__(self):
        """如果值是整数，支持 int(a) 转换"""
        return int(self._value)

    def __str__(self):
        """支持 str(a) 转换"""
        return str(self._value)
