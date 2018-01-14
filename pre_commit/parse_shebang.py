from __future__ import absolute_import
from __future__ import unicode_literals

import os.path

from identify.identify import parse_shebang_from_file


class ExecutableNotFoundError(OSError):
    def to_output(self):
        return (1, self.args[0].encode('UTF-8'), b'')


def parse_filename(filename):
    if not os.path.exists(filename):
        return ()
    else:
        return parse_shebang_from_file(filename)


def find_executable(exe, _environ=None):
    exe = os.path.normpath(exe)
    if os.sep in exe:
        return exe

    environ = _environ if _environ is not None else os.environ

    if 'PATHEXT' in environ:
        possible_exe_names = tuple(
            exe + ext.lower() for ext in environ['PATHEXT'].split(os.pathsep)
        ) + (exe,)

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
                'Executable `{}` not found'.format(orig_exe),
            )
        return exe
    else:
        return orig_exe


def normalize_cmd(cmd):
    """Fixes for the following issues on windows
    - https://bugs.python.org/issue8557
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
