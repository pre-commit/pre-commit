from __future__ import unicode_literals

import contextlib
import os
import sys

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import UNSET
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.languages.python import get_default_version  # noqa: F401
from pre_commit.languages.python import norm_version
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'py_venv'


def bin_dir(venv):
    """On windows there's a different directory for the virtualenv"""
    bin_part = 'Scripts' if os.name == 'nt' else 'bin'
    return os.path.join(venv, bin_part)


def get_env_patch(venv):
    return (
        ('PYTHONHOME', UNSET),
        ('VIRTUAL_ENV', venv),
        ('PATH', (bin_dir(venv), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(prefix, language_version):
    envdir = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, language_version),
    )
    with envcontext(get_env_patch(envdir)):
        yield


def healthy(prefix, language_version):
    with in_env(prefix, language_version):
        retcode, _, _ = cmd_output(
            'python', '-c', 'import ctypes, datetime, io, os, ssl, weakref',
            retcode=None,
        )
    return retcode == 0


def install_environment(prefix, version, additional_dependencies):
    additional_dependencies = tuple(additional_dependencies)
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    # Install a virtualenv
    env_dir = prefix.path(directory)
    with clean_path_on_failure(env_dir):
        if version != 'default':
            executable = norm_version(version)
        else:
            executable = os.path.realpath(sys.executable)
        cmd_output(executable, '-m', 'venv', env_dir, cwd='/')
        with in_env(prefix, version):
            helpers.run_setup_cmd(
                prefix, ('pip', 'install', '.') + additional_dependencies,
            )


def run_hook(prefix, hook, file_args):
    with in_env(prefix, hook['language_version']):
        return xargs(helpers.to_cmd(hook), file_args)
