from __future__ import annotations

import contextlib
import functools
import os
import sys
from collections.abc import Generator
from collections.abc import Sequence

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import UNSET
from pre_commit.envcontext import Var
from pre_commit.languages.python import bin_dir
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b
from pre_commit.util import rmtree

ENVIRONMENT_DIR = 'bun_env'
run_hook = lang_base.basic_run_hook


@functools.lru_cache(maxsize=1)
def get_default_version() -> str:
    # nodeenv does not yet support `-n system` on windows
    if sys.platform == 'win32':
        return C.DEFAULT
    # if node is already installed, we can save a bunch of setup time by
    # using the installed version
    elif lang_base.exe_exists('bun'):
        return 'system'
    else:
        return C.DEFAULT


def get_env_patch(venv: str) -> PatchesT:
    if sys.platform == 'cygwin':  # pragma: no cover
        _, win_venv, _ = cmd_output('cygpath', '-w', venv)
        install_prefix = fr'{win_venv.strip()}\bin'
        lib_dir = 'lib'
    elif sys.platform == 'win32':  # pragma: no cover
        install_prefix = bin_dir(venv)
        lib_dir = 'Scripts'
    else:  # pragma: win32 no cover
        install_prefix = venv
        lib_dir = 'lib'
    return (
        ('NODE_VIRTUAL_ENV', venv),
        ('NPM_CONFIG_PREFIX', install_prefix),
        ('npm_config_prefix', install_prefix),
        ('NPM_CONFIG_USERCONFIG', UNSET),
        ('npm_config_userconfig', UNSET),
        ('NODE_PATH', os.path.join(venv, lib_dir, 'node_modules')),
        ('PATH', (bin_dir(venv), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None]:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def health_check(prefix: Prefix, version: str) -> str | None:
    with in_env(prefix, version):
        retcode, _, _ = cmd_output_b('bun', '--version', check=False)
        if retcode != 0:  # pragma: win32 no cover
            return f'`bun --version` returned {retcode}'
        else:
            return None


def install_environment(
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:
    assert prefix.exists('package.json')
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)

    if sys.platform == 'win32':  # pragma: no cover
        envdir = fr'\\?\{os.path.normpath(envdir)}'
    cmd = [sys.executable, '-mnodeenv', '--prebuilt', '--clean-src', envdir]
    if version != C.DEFAULT:
        cmd.extend(['-n', version])
    cmd_output_b(*cmd)

    with in_env(prefix, version):
        install = (
            'bun', 'install', '--no-progress', '--silent', '--no-save',
        )
        lang_base.setup_cmd(prefix, install)

        if prefix.exists('node_modules'):  # pragma: win32 no cover
            rmtree(prefix.path('node_modules'))
