from __future__ import annotations

import contextlib
import os.path
from typing import Generator
from typing import Sequence

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.errors import FatalError
from pre_commit.languages import helpers
from pre_commit.parse_shebang import find_executable
from pre_commit.prefix import Prefix

ENVIRONMENT_DIR = 'coursier'

get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check
run_hook = helpers.basic_run_hook


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    helpers.assert_version_default('coursier', version)

    # Support both possible executable names (either "cs" or "coursier")
    executable = find_executable('cs') or find_executable('coursier')
    if executable is None:
        raise AssertionError(
            'pre-commit requires system-installed "cs" or "coursier" '
            'executables in the application search path',
        )

    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)
    channel = prefix.path('.pre-commit-channel')
    if os.path.isdir(channel):
        for app_descriptor in os.listdir(channel):
            _, app_file = os.path.split(app_descriptor)
            app, _ = os.path.splitext(app_file)
            helpers.run_setup_cmd(
                prefix,
                (
                    executable,
                    'install',
                    '--default-channels=false',
                    '--channel', channel,
                    '--dir', envdir,
                    app,
                ),
            )
    elif not additional_dependencies:
        raise FatalError(
            'expected .pre-commit-channel dir or additional_dependencies',
        )

    if additional_dependencies:
        install_cmd = (
            executable, 'install', '--dir', envdir, *additional_dependencies,
        )
        helpers.run_setup_cmd(prefix, install_cmd)


def get_env_patch(target_dir: str) -> PatchesT:
    return (
        ('PATH', (target_dir, os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield
