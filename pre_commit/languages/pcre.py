from __future__ import unicode_literals

from sys import platform

from pre_commit.languages import helpers
from pre_commit.util import shell_escape


ENVIRONMENT_DIR = None


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    """Installation for pcre type is a noop."""
    raise AssertionError('Cannot install pcre repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    grep_command = '{0} -H -n -P'.format(
        'ggrep' if platform == 'darwin' else 'grep',
    )

    # For PCRE the entry is the regular expression to match
    return helpers.run_hook(
        (
            'sh', '-c',
            # Grep usually returns 0 for matches, and nonzero for non-matches
            # so we flip it here.
            '! {0} {1} {2} $@'.format(
                grep_command, ' '.join(hook['args']),
                shell_escape(hook['entry']),
            ),
            '--',
        ),
        file_args,
    )
