from __future__ import unicode_literals

from sys import platform

from pre_commit.languages.helpers import file_args_to_stdin
from pre_commit.util import shell_escape


ENVIRONMENT_DIR = None


def install_environment(repo_cmd_runner, version='default'):
    """Installation for pcre type is a noop."""
    raise AssertionError('Cannot install pcre repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    grep_command = 'grep -H -n -P'
    if platform == 'darwin':
        grep_command = 'ggrep -H -n -P'

    # For PCRE the entry is the regular expression to match
    return repo_cmd_runner.run(
        [
            'xargs', '-0', 'sh', '-c',
            # Grep usually returns 0 for matches, and nonzero for non-matches
            # so we flip it here.
            '! {0} {1} $@'.format(grep_command, shell_escape(hook['entry'])),
            '--',
        ],
        stdin=file_args_to_stdin(file_args),
        retcode=None,
        encoding=None,
    )
