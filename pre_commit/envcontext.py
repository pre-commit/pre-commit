from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import contextlib
import os


UNSET = collections.namedtuple('UNSET', ())()


Var = collections.namedtuple('Var', ('name', 'default'))
Var.__new__.__defaults__ = ('',)


def format_env(parts, env):
    return ''.join(
        env.get(part.name, part.default) if isinstance(part, Var) else part
        for part in parts
    )


@contextlib.contextmanager
def envcontext(patch, _env=None):
    """In this context, `os.environ` is modified according to `patch`.

    `patch` is an iterable of 2-tuples (key, value):
        `key`: string
        `value`:
            - string: `environ[key] == value` inside the context.
            - UNSET: `key not in environ` inside the context.
            - template: A template is a tuple of strings and Var which will be
              replaced with the previous environment
    """
    env = os.environ if _env is None else _env
    before = env.copy()

    for k, v in patch:
        if v is UNSET:
            env.pop(k, None)
        elif isinstance(v, tuple):
            env[k] = format_env(v, before)
        else:
            env[k] = v

    try:
        yield
    finally:
        env.clear()
        env.update(before)
