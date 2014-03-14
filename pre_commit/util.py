
class cached_property(object):
    """Like @property, but caches the value."""

    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self._func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = self._func(obj)
        obj.__dict__[self.__name__] = value
        return value
