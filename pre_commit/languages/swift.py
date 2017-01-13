from __future__ import unicode_literals

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cwd
from pre_commit.languages import helpers
from pre_commit.xargs import xargs

ENVIRONMENT_DIR = None
BUILD_DIR = '.build'
BUILD_CONFIG = 'release'

def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    # Build the swift package
    with clean_path_on_failure(repo_cmd_runner.path(BUILD_DIR)):
        repo_cmd_runner.run((
            'swift', 'build',
            '-C', '{prefix}',
            '-c', BUILD_CONFIG,
            '--build-path', repo_cmd_runner.path(BUILD_DIR),
        ))

def run_hook(repo_cmd_runner, hook, file_args):
    with(cwd(repo_cmd_runner.path(BUILD_DIR, BUILD_CONFIG))):
        return xargs(helpers.to_cmd(hook), file_args)
