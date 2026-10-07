class cached_property(property):
    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        super().__init__(fget, fset, fdel, doc)
        self._name: str | None = None
        self._dependents: list[cached_property] = []   # 依赖本属性的属性

    def __set_name__(self, owner: type, name: str) -> None:
        self._name = name

    def depends(self, prop: cached_property) -> cached_property:
        if not isinstance(prop, cached_property):
            raise TypeError('depends 只能用于 CachedProperty')
        prop._dependents.append(self)
        return prop

    @property
    def _cache_key(self) -> str:
        return f'__cached_{self._name}'

    def _invalidate(self, obj, seen: set[int] | None = None) -> None:
        """清除自己 + 递归清除依赖者的缓存。"""
        if seen is None:
            seen = set()
        if id(self) in seen:          # 防循环依赖
            return
        seen.add(id(self))

        obj.__dict__.pop(self._cache_key, None)   # 清自己

        for dep in self._dependents:               # 级联
            dep._invalidate(obj, seen)

    def __get__(self, obj, objtype: type | None = None):
        if obj is None:
            return self
        cache = obj.__dict__
        key = self._cache_key
        if key in cache:
            return cache[key]
        result = self.fget(obj)
        cache[key] = result
        return result

    def __set__(self, obj, value):
        if obj is None:
            raise AttributeError(f"can't set attribute '{self._name}'")
        if self.fset is None:
            raise AttributeError(f"can't set attribute '{self._name}'")
        self.fset(obj, value)       # 先执行用户逻辑（可读旧缓存）
        self._invalidate(obj)       # 成功后级联清缓存

    def __delete__(self, obj):
        if obj is None:
            raise AttributeError(f"can't delete attribute '{self._name}'")
        if self.fdel is not None:
            self.fdel(obj)
        self._invalidate(obj)

    # ---- 保持 setter/deleter 返回 CachedProperty ----
    def setter(self, fset):
        return self._clone(fset=fset)

    def deleter(self, fdel):
        return self._clone(fdel=fdel)

    def _clone(self, fget=None, fset=None, fdel=None) -> 'cached_property':
        new = type(self)(
            fget if fget is not None else self.fget,
            fset if fset is not None else self.fset,
            fdel if fdel is not None else self.fdel,
            self.__doc__,
        )
        new._name = self._name
        new._dependents = list(self._dependents)
        return new