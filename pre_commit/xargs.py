from __future__ import absolute_import
from __future__ import unicode_literals

from pre_commit.util import cmd_output


# Limit used previously to avoid "xargs ... Bad file number" on windows
# This is slightly less than the posix mandated minimum
MAX_LENGTH = 4000


class ArgumentTooLongError(RuntimeError):
    pass


def partition(cmd, varargs, _max_length=MAX_LENGTH):
    cmd = tuple(cmd)
    ret = []

    ret_cmd = []
    total_len = len(' '.join(cmd))
    # Reversed so arguments are in order
    varargs = list(reversed(varargs))

    while varargs:
        arg = varargs.pop()

        if total_len + 1 + len(arg) <= _max_length:
            ret_cmd.append(arg)
            total_len += len(arg)
        elif not ret_cmd:
            raise ArgumentTooLongError(arg)
        else:
            # We've exceeded the length, yield a command
            ret.append(cmd + tuple(ret_cmd))
            ret_cmd = []
            total_len = len(' '.join(cmd))
            varargs.append(arg)

    ret.append(cmd + tuple(ret_cmd))

    return tuple(ret)


def xargs(cmd, varargs):
    """A simplified implementation of xargs."""
    retcode = 0
    stdout = b''
    stderr = b''

    for run_cmd in partition(cmd, varargs):
        proc_retcode, proc_out, proc_err = cmd_output(
            *run_cmd, encoding=None, retcode=None
        )
        retcode |= proc_retcode
        stdout += proc_out
        stderr += proc_err

    return retcode, stdout, stderr
