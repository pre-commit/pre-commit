from __future__ import annotations

import contextlib
import os
from typing import Generator
from typing import Sequence

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
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
) -> None:   # pragma: win32 no cover
    helpers.assert_version_default('coursier', version)
    helpers.assert_no_additional_deps('coursier', additional_dependencies)

    # Support both possible executable names (either "cs" or "coursier")
    executable = find_executable('cs') or find_executable('coursier')
    if executable is None:
        raise AssertionError(
            'pre-commit requires system-installed "cs" or "coursier" '
            'executables in the application search path',
        )

    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)
    channel = prefix.path('.pre-commit-channel')
    for app_descriptor in os.listdir(channel):
        _, app_file = os.path.split(app_descriptor)
        app, _ = os.path.splitext(app_file)
        helpers.run_setup_cmd(
            prefix,
            (
                executable,
                'install',
                '--default-channels=false',
                f'--channel={channel}',
                app,
                f'--dir={envdir}',
            ),
        )


def get_env_patch(target_dir: str) -> PatchesT:   # pragma: win32 no cover
    return (
        ('PATH', (target_dir, os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager  # pragma: win32 no cover
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield
