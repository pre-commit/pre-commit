from __future__ import annotations

import contextlib
import os
from typing import Generator
from typing import Sequence

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import SubstitutionT
from pre_commit.envcontext import UNSET
from pre_commit.envcontext import Var
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'conda'
get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check


def get_env_patch(env: str) -> PatchesT:
    # On non-windows systems executable live in $CONDA_PREFIX/bin, on Windows
    # they can be in $CONDA_PREFIX/bin, $CONDA_PREFIX/Library/bin,
    # $CONDA_PREFIX/Scripts and $CONDA_PREFIX. Whereas the latter only
    # seems to be used for python.exe.
    path: SubstitutionT = (os.path.join(env, 'bin'), os.pathsep, Var('PATH'))
    if os.name == 'nt':  # pragma: no cover (platform specific)
        path = (env, os.pathsep, *path)
        path = (os.path.join(env, 'Scripts'), os.pathsep, *path)
        path = (os.path.join(env, 'Library', 'bin'), os.pathsep, *path)

    return (
        ('PYTHONHOME', UNSET),
        ('VIRTUAL_ENV', UNSET),
        ('CONDA_PREFIX', env),
        ('PATH', path),
    )


@contextlib.contextmanager
def in_env(
        prefix: Prefix,
        language_version: str,
) -> Generator[None, None, None]:
    directory = helpers.environment_dir(ENVIRONMENT_DIR, language_version)
    envdir = prefix.path(directory)
    with envcontext(get_env_patch(envdir)):
        yield


def _conda_exe() -> str:
    if os.environ.get('PRE_COMMIT_USE_MICROMAMBA'):
        return 'micromamba'
    elif os.environ.get('PRE_COMMIT_USE_MAMBA'):
        return 'mamba'
    else:
        return 'conda'


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    helpers.assert_version_default('conda', version)
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    conda_exe = _conda_exe()

    env_dir = prefix.path(directory)
    with clean_path_on_failure(env_dir):
        cmd_output_b(
            conda_exe, 'env', 'create', '-p', env_dir, '--file',
            'environment.yml', cwd=prefix.prefix_dir,
        )
        if additional_dependencies:
            conda_dependancies = [
                conda_dep.split()[-1]
                for conda_dep in additional_dependencies
                if not conda_dep.startswith('pip install')
            ]
            pip_dependancies = [
                pip_dep.split()[-1]
                for pip_dep in additional_dependencies
                if pip_dep.startswith('pip install')
            ]
            if conda_dependancies:
                cmd_output_b(
                    conda_exe, 'install', '-p', env_dir, *conda_dependancies,
                    cwd=prefix.prefix_dir,
                )
            if pip_dependancies:
                cmd_output_b(
                    conda_exe, 'run', '-p', 'pip',
                    '--yes', env_dir, *pip_dependancies,
                    cwd=prefix.prefix_dir,
                )


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> tuple[int, bytes]:
    # TODO: Some rare commands need to be run using `conda run` but mostly we
    #       can run them without which is much quicker and produces a better
    #       output.
    # cmd = ('conda', 'run', '-p', env_dir) + hook.cmd
    with in_env(hook.prefix, hook.language_version):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
