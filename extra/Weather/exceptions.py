class CityNotFound(Exception):
    """
    Exception raised when the specified city is not found.
    """
    def __init__(self, city: str | int):
        """
        :type city: str | int
        """
        self.city = city

    def __str__(self):
        return f'城市未找到: {self.city}'

    def __repr__(self):
        return f'<{self.__class__.__name__} {self.city}> at {hex(id(self))}'