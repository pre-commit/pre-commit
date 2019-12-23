from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import concurrent.futures
import contextlib
import math
import os
import subprocess
import sys

import six

from pre_commit import parse_shebang
from pre_commit.util import cmd_output_b
from pre_commit.util import cmd_output_p


def _environ_size(_env=None):
    environ = _env if _env is not None else getattr(os, 'environb', os.environ)
    size = 8 * len(environ)  # number of pointers in `envp`
    for k, v in environ.items():
        size += len(k) + len(v) + 2  # c strings in `envp`
    return size


def _get_platform_max_length():  # pragma: no cover (platform specific)
    if os.name == 'posix':
        maximum = os.sysconf(str('SC_ARG_MAX')) - 2048 - _environ_size()
        maximum = max(min(maximum, 2 ** 17), 2 ** 12)
        return maximum
    elif os.name == 'nt':
        return 2 ** 15 - 2048  # UNICODE_STRING max - headroom
    else:
        # posix minimum
        return 2 ** 12


def _command_length(*cmd):
    full_cmd = ' '.join(cmd)

    # win32 uses the amount of characters, more details at:
    # https://github.com/pre-commit/pre-commit/pull/839
    if sys.platform == 'win32':
        # the python2.x apis require bytes, we encode as UTF-8
        if six.PY2:
            return len(full_cmd.encode('utf-8'))
        else:
            return len(full_cmd.encode('utf-16le')) // 2
    else:
        return len(full_cmd.encode(sys.getfilesystemencoding()))


class ArgumentTooLongError(RuntimeError):
    pass


def partition(cmd, varargs, target_concurrency, _max_length=None):
    _max_length = _max_length or _get_platform_max_length()

    # Generally, we try to partition evenly into at least `target_concurrency`
    # partitions, but we don't want a bunch of tiny partitions.
    max_args = max(4, math.ceil(len(varargs) / target_concurrency))

    cmd = tuple(cmd)
    ret = []

    ret_cmd = []
    # Reversed so arguments are in order
    varargs = list(reversed(varargs))

    total_length = _command_length(*cmd) + 1
    while varargs:
        arg = varargs.pop()

        arg_length = _command_length(arg) + 1
        if (
                total_length + arg_length <= _max_length and
                len(ret_cmd) < max_args
        ):
            ret_cmd.append(arg)
            total_length += arg_length
        elif not ret_cmd:
            raise ArgumentTooLongError(arg)
        else:
            # We've exceeded the length, yield a command
            ret.append(cmd + tuple(ret_cmd))
            ret_cmd = []
            total_length = _command_length(*cmd) + 1
            varargs.append(arg)

    ret.append(cmd + tuple(ret_cmd))

    return tuple(ret)


@contextlib.contextmanager
def _thread_mapper(maxsize):
    if maxsize == 1:
        yield map
    else:
        with concurrent.futures.ThreadPoolExecutor(maxsize) as ex:
            yield ex.map


def xargs(cmd, varargs, **kwargs):
    """A simplified implementation of xargs.

    color: Make a pty if on a platform that supports it
    negate: Make nonzero successful and zero a failure
    target_concurrency: Target number of partitions to run concurrently
    """
    color = kwargs.pop('color', False)
    negate = kwargs.pop('negate', False)
    target_concurrency = kwargs.pop('target_concurrency', 1)
    max_length = kwargs.pop('_max_length', _get_platform_max_length())
    cmd_fn = cmd_output_p if color else cmd_output_b
    retcode = 0
    stdout = b''

    try:
        cmd = parse_shebang.normalize_cmd(cmd)
    except parse_shebang.ExecutableNotFoundError as e:
        return e.to_output()[:2]

    partitions = partition(cmd, varargs, target_concurrency, max_length)

    def run_cmd_partition(run_cmd):
        return cmd_fn(
            *run_cmd, retcode=None, stderr=subprocess.STDOUT, **kwargs
        )

    threads = min(len(partitions), target_concurrency)
    with _thread_mapper(threads) as thread_map:
        results = thread_map(run_cmd_partition, partitions)

        for proc_retcode, proc_out, _ in results:
            if negate:
                proc_retcode = not proc_retcode
            retcode = max(retcode, proc_retcode)
            stdout += proc_out

    return retcode, stdout
