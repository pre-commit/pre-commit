from __future__ import absolute_import
from __future__ import unicode_literals

import os.path

from identify.identify import parse_shebang_from_file
from identify.identify import tags_from_path

from pre_commit import ShelPathConv


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


def normexe(orig):
    def _error(msg):
        raise ExecutableNotFoundError('Executable `{}` {}'.format(orig, msg))

    if os.sep not in orig and (not os.altsep or os.altsep not in orig):
        exe = find_executable(orig)
        if exe is None:
            _error('not found')
        return exe
    elif os.path.isdir(orig):
        _error('is a directory')
    elif not os.path.isfile(orig):
        _error('not found')
    elif not os.access(orig, os.X_OK):  # pragma: windows no cover
        _error('is not executable')
    else:
        return orig


def normalize_cmd(cmd):
    """Fixes for the following issues on windows
    - https://bugs.python.org/issue8557
    - windows does not parse shebangs

    This function also makes deep-path shebangs work just fine
    """
    # Use PATH to determine the executable
    exe = normexe(cmd[0])

    convert = 'shell' in tags_from_path(exe)

    # Figure out the shebang from the resulting command
    cmd = parse_filename(exe) + (exe,) + cmd[1:]

    # This could have given us back another bare executable
    exe = normexe(cmd[0])
    cmd = (exe,) + cmd[1:]
    return ShelPathConv.ConvertArgs(*cmd) if convert else cmd
