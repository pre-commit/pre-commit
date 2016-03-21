from __future__ import unicode_literals

import shlex

from pre_commit.languages import helpers


ENVIRONMENT_DIR = None


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    """Installation for system type is a noop."""
    raise AssertionError('Cannot install system repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    return helpers.run_hook(
        tuple(shlex.split(hook['entry'])) + tuple(hook['args']), file_args,
    )
