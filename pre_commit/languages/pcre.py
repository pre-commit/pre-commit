from __future__ import unicode_literals

from sys import platform

from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    """Installation for pcre type is a noop."""
    raise AssertionError('Cannot install pcre repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    # For PCRE the entry is the regular expression to match
    cmd = (
        'ggrep' if platform == 'darwin' else 'grep',
        '-H', '-n', '-P',
    ) + tuple(hook['args']) + (hook['entry'],)

    # Grep usually returns 0 for matches, and nonzero for non-matches so we
    # negate it here.
    return xargs(cmd, file_args, negate=True)
