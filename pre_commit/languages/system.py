from __future__ import unicode_literals

import shlex

from pre_commit.languages.helpers import file_args_to_stdin


ENVIRONMENT_DIR = None


def install_environment(repo_cmd_runner, version='default'):
    """Installation for system type is a noop."""
    raise AssertionError('Cannot install system repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    return repo_cmd_runner.run(
        ['xargs', '-0'] + shlex.split(hook['entry']) + hook['args'],
        stdin=file_args_to_stdin(file_args),
        retcode=None,
        encoding=None,
    )
