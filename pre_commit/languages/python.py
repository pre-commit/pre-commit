from __future__ import unicode_literals

import contextlib
import os
import sys

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import UNSET
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.parse_shebang import find_executable
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
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
def in_env(prefix, language_version):
    envdir = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, language_version),
    )
    with envcontext(get_env_patch(envdir)):
        yield


def _find_by_py_launcher(version):  # pragma: no cover (windows only)
    if version.startswith('python'):
        try:
            return cmd_output(
                'py', '-{}'.format(version[len('python'):]),
                '-c', 'import sys; print(sys.executable)',
            )[1].strip()
        except CalledProcessError:
            pass


def _get_default_version():  # pragma: no cover (platform dependent)
    def _norm(path):
        _, exe = os.path.split(path.lower())
        exe, _, _ = exe.partition('.exe')
        if find_executable(exe) and exe not in {'python', 'pythonw'}:
            return exe

    # First attempt from `sys.executable` (or the realpath)
    # On linux, I see these common sys.executables:
    #
    # system `python`: /usr/bin/python -> python2.7
    # system `python2`: /usr/bin/python2 -> python2.7
    # virtualenv v: v/bin/python (will not return from this loop)
    # virtualenv v -ppython2: v/bin/python -> python2
    # virtualenv v -ppython2.7: v/bin/python -> python2.7
    # virtualenv v -ppypy: v/bin/python -> v/bin/pypy
    for path in {sys.executable, os.path.realpath(sys.executable)}:
        exe = _norm(path)
        if exe:
            return exe

    # Next try the `pythonX.X` executable
    exe = 'python{}.{}'.format(*sys.version_info)
    if find_executable(exe):
        return exe

    if _find_by_py_launcher(exe):
        return exe

    # Give a best-effort try for windows
    if os.path.exists(r'C:\{}\python.exe'.format(exe.replace('.', ''))):
        return exe

    # We tried!
    return 'default'


def get_default_version():
    # TODO: when dropping python2, use `functools.lru_cache(maxsize=1)`
    try:
        return get_default_version.cached_version
    except AttributeError:
        get_default_version.cached_version = _get_default_version()
        return get_default_version()


def healthy(prefix, language_version):
    with in_env(prefix, language_version):
        retcode, _, _ = cmd_output(
            'python', '-c', 'import ctypes, datetime, io, os, ssl, weakref',
            retcode=None,
        )
    return retcode == 0


def norm_version(version):
    if os.name == 'nt':  # pragma: no cover (windows)
        # Try looking up by name
        version_exec = find_executable(version)
        if version_exec and version_exec != version:
            return version_exec

        version_exec = _find_by_py_launcher(version)
        if version_exec:
            return version_exec

        # If it is in the form pythonx.x search in the default
        # place on windows
        if version.startswith('python'):
            return r'C:\{}\python.exe'.format(version.replace('.', ''))

        # Otherwise assume it is a path
    return os.path.expanduser(version)


def install_environment(prefix, version, additional_dependencies):
    additional_dependencies = tuple(additional_dependencies)
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    # Install a virtualenv
    env_dir = prefix.path(directory)
    with clean_path_on_failure(env_dir):
        venv_cmd = [sys.executable, '-m', 'virtualenv', env_dir]
        if version != 'default':
            venv_cmd.extend(['-p', norm_version(version)])
        else:
            venv_cmd.extend(['-p', os.path.realpath(sys.executable)])
        venv_env = dict(os.environ, VIRTUALENV_NO_DOWNLOAD='1')
        cmd_output(*venv_cmd, cwd='/', env=venv_env)
        with in_env(prefix, version):
            helpers.run_setup_cmd(
                prefix, ('pip', 'install', '.') + additional_dependencies,
            )


def run_hook(prefix, hook, file_args):
    with in_env(prefix, hook['language_version']):
        return xargs(helpers.to_cmd(hook), file_args)
