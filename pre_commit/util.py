
import functools
import os
import sys


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


def memoize_by_cwd(func):
    """Memoize a function call based on os.getcwd()."""
    @functools.wraps(func)
    def wrapper(*args):
        cwd = os.getcwd()
        key = (cwd,) + args
        try:
            return wrapper._cache[key]
        except KeyError:
            ret = wrapper._cache[key] = func(*args)
            return ret

    wrapper._cache = {}

    return wrapper


def entry(func):
    """Allows a function that has `argv` as an argument to be used as a
    commandline entry.  This will make the function callable using either
    explicitly passed argv or defaulting to sys.argv[1:]
    """
    @functools.wraps(func)
    def wrapper(argv=None):
        if argv is None:
            argv = sys.argv[1:]
        return func(argv)
    return wrapper
