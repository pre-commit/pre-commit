from __future__ import unicode_literals

from pre_commit.languages import helpers
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    """Installation for system type is a noop."""
    raise AssertionError('Cannot install system repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    return xargs(helpers.to_cmd(hook), file_args)
