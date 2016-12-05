from __future__ import absolute_import
from __future__ import unicode_literals

from pre_commit import parse_shebang
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
