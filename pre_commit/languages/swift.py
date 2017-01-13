from __future__ import unicode_literals

import contextlib
import os

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.xargs import xargs

ENVIRONMENT_DIR = 'swift_env'
BUILD_DIR = '.build'
BUILD_CONFIG = 'release'


def get_env_patch(venv):
    bin_path = os.path.join(venv, BUILD_DIR, BUILD_CONFIG)
    patches = (
        ('PATH', (
            bin_path, os.pathsep, Var('PATH'),
        )),
    )
    return patches


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    envdir = os.path.join(
        repo_cmd_runner.prefix_dir,
        helpers.environment_dir(ENVIRONMENT_DIR, 'default'),
    )
    with envcontext(get_env_patch(envdir)):
        yield


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    assert version == 'default', (
        'Pre-commit does not support language_version for docker '
    )
    directory = repo_cmd_runner.path(helpers.environment_dir(
        ENVIRONMENT_DIR, 'default',
    ))

    # Build the swift package
    with clean_path_on_failure(directory):
        os.mkdir(directory)
        repo_cmd_runner.run((
            'swift', 'build',
            '-C', '{prefix}',
            '-c', BUILD_CONFIG,
            '--build-path', os.path.join(directory, BUILD_DIR),
        ))


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner):
        return xargs(helpers.to_cmd(hook), file_args)
