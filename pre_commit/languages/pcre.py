from __future__ import unicode_literals

import sys

from pre_commit.languages import helpers
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None
GREP = 'ggrep' if sys.platform == 'darwin' else 'grep'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def install_environment(repo_cmd_runner, version, additional_dependencies):
    """Installation for pcre type is a noop."""
    raise AssertionError('Cannot install pcre repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    # For PCRE the entry is the regular expression to match
    cmd = (GREP, '-H', '-n', '-P') + tuple(hook['args']) + (hook['entry'],)

    # Grep usually returns 0 for matches, and nonzero for non-matches so we
    # negate it here.
    return xargs(cmd, file_args, negate=True)
