from __future__ import unicode_literals

import os.path

from pre_commit.languages import python
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output


ENVIRONMENT_DIR = 'py_venv'


def orig_py_exe(exe):  # pragma: no cover (platform specific)
    """A -mvenv virtualenv made from a -mvirtualenv virtualenv installs
    packages to the incorrect location.  Attempt to find the _original_ exe
    and invoke `-mvenv` from there.

    See:
    - https://github.com/pre-commit/pre-commit/issues/755
    - https://github.com/pypa/virtualenv/issues/1095
    - https://bugs.python.org/issue30811
    """
    try:
        prefix_script = 'import sys; print(sys.real_prefix)'
        _, prefix, _ = cmd_output(exe, '-c', prefix_script)
        prefix = prefix.strip()
    except CalledProcessError:
        # not created from -mvirtualenv
        return exe

    if os.name == 'nt':
        expected = os.path.join(prefix, 'python.exe')
    else:
        expected = os.path.join(prefix, 'bin', os.path.basename(exe))

    if os.path.exists(expected):
        return expected
    else:
        return exe


def make_venv(envdir, python):
    cmd_output(orig_py_exe(python), '-mvenv', envdir, cwd='/')


get_default_version = python.get_default_version
_interface = python.py_interface(ENVIRONMENT_DIR, make_venv)
in_env, healthy, run_hook, install_environment = _interface
