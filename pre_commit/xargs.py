from __future__ import absolute_import
from __future__ import unicode_literals

import sys

from pre_commit import parse_shebang
from pre_commit.util import cmd_output


# TODO: properly compute max_length value
def _get_platform_max_length():
    # posix minimum
    return 4 * 1024


def _command_length(*cmd):
    full_cmd = ' '.join(cmd)

    # win32 uses the amount of characters, more details at:
    # https://blogs.msdn.microsoft.com/oldnewthing/20031210-00/?p=41553/
    if sys.platform == 'win32':
        return len(full_cmd)

    return len(full_cmd.encode(sys.getfilesystemencoding()))


class ArgumentTooLongError(RuntimeError):
    pass


def partition(cmd, varargs, _max_length=None):
    _max_length = _max_length or _get_platform_max_length()
    cmd = tuple(cmd)
    ret = []

    ret_cmd = []
    # Reversed so arguments are in order
    varargs = list(reversed(varargs))

    total_length = _command_length(*cmd)
    while varargs:
        arg = varargs.pop()

        arg_length = _command_length(arg) + 1
        if total_length + arg_length <= _max_length:
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


def xargs(cmd, varargs, **kwargs):
    """A simplified implementation of xargs.

    negate: Make nonzero successful and zero a failure
    """
    negate = kwargs.pop('negate', False)
    retcode = 0
    stdout = b''
    stderr = b''

    try:
        parse_shebang.normexe(cmd[0])
    except parse_shebang.ExecutableNotFoundError as e:
        return e.to_output()

    for run_cmd in partition(cmd, varargs, **kwargs):
        proc_retcode, proc_out, proc_err = cmd_output(
            *run_cmd, encoding=None, retcode=None
        )
        # This is *slightly* too clever so I'll explain it.
        # First the xor boolean table:
        #     T | F |
        #   +-------+
        # T | F | T |
        # --+-------+
        # F | T | F |
        # --+-------+
        # When negate is True, it has the effect of flipping the return code
        # Otherwise, the retuncode is unchanged
        retcode |= bool(proc_retcode) ^ negate
        stdout += proc_out
        stderr += proc_err

    return retcode, stdout, stderr
