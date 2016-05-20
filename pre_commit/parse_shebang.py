from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os.path
import shlex
import string

from pre_commit import five


printable = frozenset(string.printable)


class ExecutableNotFoundError(OSError):
    pass


def parse_bytesio(bytesio):
    """Parse the shebang from a file opened for reading binary."""
    if bytesio.read(2) != b'#!':
        return ()
    first_line = bytesio.readline()
    try:
        first_line = first_line.decode('US-ASCII')
    except UnicodeDecodeError:
        return ()

    # Require only printable ascii
    for c in first_line:
        if c not in printable:
            return ()

    # shlex.split is horribly broken in py26 on text strings
    cmd = tuple(shlex.split(five.n(first_line)))
    if cmd[0] == '/usr/bin/env':
        cmd = cmd[1:]
    return cmd


def parse_filename(filename):
    """Parse the shebang given a filename."""
    if not os.path.exists(filename) or not os.access(filename, os.X_OK):
        return ()

    with io.open(filename, 'rb') as f:
        return parse_bytesio(f)


def find_executable(exe, _environ=None):
    exe = os.path.normpath(exe)
    if os.sep in exe:
        return exe

    environ = _environ if _environ is not None else os.environ

    if 'PATHEXT' in environ:
        possible_exe_names = (exe,) + tuple(
            exe + ext.lower() for ext in environ['PATHEXT'].split(os.pathsep)
        )
    else:
        possible_exe_names = (exe,)

    for path in environ.get('PATH', '').split(os.pathsep):
        for possible_exe_name in possible_exe_names:
            joined = os.path.join(path, possible_exe_name)
            if os.path.isfile(joined) and os.access(joined, os.X_OK):
                return joined
    else:
        return None


def normexe(orig_exe):
    if os.sep not in orig_exe:
        exe = find_executable(orig_exe)
        if exe is None:
            raise ExecutableNotFoundError(
                'Executable `{0}` not found'.format(orig_exe),
            )
        return exe
    else:
        return orig_exe


def normalize_cmd(cmd):
    """Fixes for the following issues on windows
    - http://bugs.python.org/issue8557
    - windows does not parse shebangs

    This function also makes deep-path shebangs work just fine
    """
    # Use PATH to determine the executable
    exe = normexe(cmd[0])

    # Figure out the shebang from the resulting command
    cmd = parse_filename(exe) + (exe,) + cmd[1:]

    # This could have given us back another bare executable
    exe = normexe(cmd[0])

    return (exe,) + cmd[1:]
