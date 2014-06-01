import contextlib
import functools
import os
import os.path
import shutil
import sys


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


@contextlib.contextmanager
def clean_path_on_failure(path):
    """Cleans up the directory on an exceptional failure."""
    try:
        yield
    except BaseException:
        if os.path.exists(path):
            shutil.rmtree(path)
        raise


# TODO: asottile.contextlib this with a forward port of nested
@contextlib.contextmanager
def noop_context():
    yield
