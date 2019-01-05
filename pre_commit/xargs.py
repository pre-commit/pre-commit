from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import concurrent.futures
import contextlib
import math
import sys

import six

from pre_commit import parse_shebang
from pre_commit.util import cmd_output


# TODO: properly compute max_length value
def _get_platform_max_length():
    # posix minimum
    return 4 * 1024


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

    total_length = _command_length(*cmd)
    while varargs:
        arg = varargs.pop()

        arg_length = _command_length(arg) + 1
        if (
                total_length + arg_length <= _max_length
                and len(ret_cmd) < max_args
        ):
            ret_cmd.append(arg)
            total_length += arg_length
        elif not ret_cmd:
            raise ArgumentTooLongError(arg)
        else:
            # We've exceeded the length, yield a command
            ret.append(cmd + tuple(ret_cmd))
            ret_cmd = []
            total_length = _command_length(*cmd)
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

    negate: Make nonzero successful and zero a failure
    target_concurrency: Target number of partitions to run concurrently
    """
    negate = kwargs.pop('negate', False)
    target_concurrency = kwargs.pop('target_concurrency', 1)
    retcode = 0
    stdout = b''
    stderr = b''

    try:
        parse_shebang.normexe(cmd[0])
    except parse_shebang.ExecutableNotFoundError as e:
        return e.to_output()

    partitions = partition(cmd, varargs, target_concurrency, **kwargs)

    def run_cmd_partition(run_cmd):
        return cmd_output(*run_cmd, encoding=None, retcode=None)

    threads = min(len(partitions), target_concurrency)
    with _thread_mapper(threads) as thread_map:
        results = thread_map(run_cmd_partition, partitions)

        for proc_retcode, proc_out, proc_err in results:
            # This is *slightly* too clever so I'll explain it.
            # First the xor boolean table:
            #     T | F |
            #   +-------+
            # T | F | T |
            # --+-------+
            # F | T | F |
            # --+-------+
            # When negate is True, it has the effect of flipping the return
            # code. Otherwise, the returncode is unchanged.
            retcode |= bool(proc_retcode) ^ negate
            stdout += proc_out
            stderr += proc_err

    return retcode, stdout, stderr
