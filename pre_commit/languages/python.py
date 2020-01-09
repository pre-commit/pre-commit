import contextlib
import os
import sys

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import UNSET
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.parse_shebang import find_executable
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b


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


def _find_by_py_launcher(version):  # pragma: no cover (windows only)
    if version.startswith('python'):
        try:
            return cmd_output(
                'py', '-{}'.format(version[len('python'):]),
                '-c', 'import sys; print(sys.executable)',
            )[1].strip()
        except CalledProcessError:
            pass


def _find_by_sys_executable():
    def _norm(path):
        _, exe = os.path.split(path.lower())
        exe, _, _ = exe.partition('.exe')
        if find_executable(exe) and exe not in {'python', 'pythonw'}:
            return exe

    # On linux, I see these common sys.executables:
    #
    # system `python`: /usr/bin/python -> python2.7
    # system `python2`: /usr/bin/python2 -> python2.7
    # virtualenv v: v/bin/python (will not return from this loop)
    # virtualenv v -ppython2: v/bin/python -> python2
    # virtualenv v -ppython2.7: v/bin/python -> python2.7
    # virtualenv v -ppypy: v/bin/python -> v/bin/pypy
    for path in (sys.executable, os.path.realpath(sys.executable)):
        exe = _norm(path)
        if exe:
            return exe
    return None


def _get_default_version():  # pragma: no cover (platform dependent)
    # First attempt from `sys.executable` (or the realpath)
    exe = _find_by_sys_executable()
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
    return C.DEFAULT


def get_default_version():
    # TODO: when dropping python2, use `functools.lru_cache(maxsize=1)`
    try:
        return get_default_version.cached_version
    except AttributeError:
        get_default_version.cached_version = _get_default_version()
        return get_default_version()


def _sys_executable_matches(version):
    if version == 'python':
        return True
    elif not version.startswith('python'):
        return False

    try:
        info = tuple(int(p) for p in version[len('python'):].split('.'))
    except ValueError:
        return False

    return sys.version_info[:len(info)] == info


def norm_version(version):
    # first see if our current executable is appropriate
    if _sys_executable_matches(version):
        return sys.executable

    if os.name == 'nt':  # pragma: no cover (windows)
        version_exec = _find_by_py_launcher(version)
        if version_exec:
            return version_exec

        # Try looking up by name
        version_exec = find_executable(version)
        if version_exec and version_exec != version:
            return version_exec

        # If it is in the form pythonx.x search in the default
        # place on windows
        if version.startswith('python'):
            return r'C:\{}\python.exe'.format(version.replace('.', ''))

    # Otherwise assume it is a path
    return os.path.expanduser(version)


def py_interface(_dir, _make_venv):
    @contextlib.contextmanager
    def in_env(prefix, language_version):
        envdir = prefix.path(helpers.environment_dir(_dir, language_version))
        with envcontext(get_env_patch(envdir)):
            yield

    def healthy(prefix, language_version):
        with in_env(prefix, language_version):
            retcode, _, _ = cmd_output_b(
                'python', '-c',
                'import ctypes, datetime, io, os, ssl, weakref',
                cwd='/',
                retcode=None,
            )
        return retcode == 0

    def run_hook(hook, file_args, color):
        with in_env(hook.prefix, hook.language_version):
            return helpers.run_xargs(hook, hook.cmd, file_args, color=color)

    def install_environment(prefix, version, additional_dependencies):
        additional_dependencies = tuple(additional_dependencies)
        directory = helpers.environment_dir(_dir, version)

        env_dir = prefix.path(directory)
        with clean_path_on_failure(env_dir):
            if version != C.DEFAULT:
                python = norm_version(version)
            else:
                python = os.path.realpath(sys.executable)
            _make_venv(env_dir, python)
            with in_env(prefix, version):
                helpers.run_setup_cmd(
                    prefix, ('pip', 'install', '.') + additional_dependencies,
                )

    return in_env, healthy, run_hook, install_environment


def make_venv(envdir, python):
    env = dict(os.environ, VIRTUALENV_NO_DOWNLOAD='1')
    cmd = (sys.executable, '-mvirtualenv', envdir, '-p', python)
    cmd_output_b(*cmd, env=env, cwd='/')


_interface = py_interface(ENVIRONMENT_DIR, make_venv)
in_env, healthy, run_hook, install_environment = _interface
