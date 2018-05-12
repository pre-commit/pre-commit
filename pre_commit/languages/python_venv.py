from __future__ import unicode_literals

from pre_commit.languages import python
from pre_commit.util import cmd_output


ENVIRONMENT_DIR = 'py_venv'


def make_venv(envdir, python):
    cmd_output(python, '-mvenv', envdir, cwd='/')


get_default_version = python.get_default_version
_interface = python.py_interface(ENVIRONMENT_DIR, make_venv)
in_env, healthy, run_hook, install_environment = _interface
