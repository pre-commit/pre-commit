from __future__ import unicode_literals

import contextlib
import distutils.spawn
import os
import sys

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import UNSET
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'py_env'


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
def in_env(repo_cmd_runner, language_version):
    envdir = repo_cmd_runner.path(
        helpers.environment_dir(ENVIRONMENT_DIR, language_version),
    )
    with envcontext(get_env_patch(envdir)):
        yield


def norm_version(version):
    if os.name == 'nt':  # pragma: no cover (windows)
        # Try looking up by name
        if distutils.spawn.find_executable(version):
            return version

        # If it is in the form pythonx.x search in the default
        # place on windows
        if version.startswith('python'):
            return r'C:\{}\python.exe'.format(version.replace('.', ''))

        # Otherwise assume it is a path
    return os.path.expanduser(version)


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    additional_dependencies = tuple(additional_dependencies)
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    # Install a virtualenv
    with clean_path_on_failure(repo_cmd_runner.path(directory)):
        venv_cmd = [
            sys.executable, '-m', 'virtualenv',
            '{{prefix}}{}'.format(directory)
        ]
        if version != 'default':
            venv_cmd.extend(['-p', norm_version(version)])
        else:
            venv_cmd.extend(['-p', os.path.realpath(sys.executable)])
        repo_cmd_runner.run(venv_cmd, cwd='/')
        with in_env(repo_cmd_runner, version):
            helpers.run_setup_cmd(
                repo_cmd_runner,
                ('pip', 'install', '.') + additional_dependencies,
            )


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner, hook['language_version']):
        return xargs(helpers.to_cmd(hook), file_args)
