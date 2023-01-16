from __future__ import annotations

import contextlib
import os
from typing import Generator
from typing import Sequence

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b

BUILD_DIR = '.build'
BUILD_CONFIG = 'release'

ENVIRONMENT_DIR = 'swift_env'
get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check
run_hook = helpers.basic_run_hook


def get_env_patch(venv: str) -> PatchesT:  # pragma: win32 no cover
    bin_path = os.path.join(venv, BUILD_DIR, BUILD_CONFIG)
    return (('PATH', (bin_path, os.pathsep, Var('PATH'))),)


@contextlib.contextmanager  # pragma: win32 no cover
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def install_environment(
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:  # pragma: win32 no cover
    helpers.assert_version_default('swift', version)
    helpers.assert_no_additional_deps('swift', additional_dependencies)
    envdir = helpers.environment_dir(prefix, ENVIRONMENT_DIR, version)

    # Build the swift package
    os.mkdir(envdir)
    cmd_output_b(
        'swift', 'build',
        '-C', prefix.prefix_dir,
        '-c', BUILD_CONFIG,
        '--build-path', os.path.join(envdir, BUILD_DIR),
    )
