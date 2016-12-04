from __future__ import unicode_literals

from sys import platform

from pre_commit.xargs import xargs

import os

ENVIRONMENT_DIR = None


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    """Installation for pcre type is a noop."""
    raise AssertionError('Cannot install pcre repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    grep_command = 'ggrep' if platform == 'darwin' else 'grep'

    # Determine if grep is installed on system
    if os.system('which ' + grep_command) != 0:
        raise AssertionError('Cannot execute grep command: ' + grep_command)

    # For PCRE the entry is the regular expression to match
    cmd = (
        grep_command,
        '-H', '-n', '-P',
    ) + tuple(hook['args']) + (hook['entry'],)

    # Grep usually returns 0 for matches, and nonzero for non-matches so we
    # negate it here.
    return xargs(cmd, file_args, negate=True)
