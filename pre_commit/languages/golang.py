from __future__ import annotations

import contextlib
import os.path
import sys
from typing import Generator
from typing import Sequence

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from pre_commit.util import rmtree

ENVIRONMENT_DIR = 'golangenv'
get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check


def get_env_patch(venv: str) -> PatchesT:
    return (
        ('PATH', (os.path.join(venv, 'bin'), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix) -> Generator[None, None, None]:
    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, C.DEFAULT)
    with envcontext(get_env_patch(envdir)):
        yield


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    helpers.assert_version_default('golang', version)
    env_dir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)

    if sys.platform == 'cygwin':  # pragma: no cover
        gopath = cmd_output('cygpath', '-w', env_dir)[1].strip()
    else:
        gopath = env_dir
    env = dict(os.environ, GOPATH=gopath)
    env.pop('GOBIN', None)

    helpers.run_setup_cmd(prefix, ('go', 'install', './...'), env=env)
    for dependency in additional_dependencies:
        helpers.run_setup_cmd(prefix, ('go', 'install', dependency), env=env)

    # save some disk space -- we don't need this after installation
    pkgdir = os.path.join(env_dir, 'pkg')
    if os.path.exists(pkgdir):  # pragma: no branch (always true on windows?)
        rmtree(pkgdir)


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> tuple[int, bytes]:
    with in_env(hook.prefix):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
