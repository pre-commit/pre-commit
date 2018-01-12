from __future__ import unicode_literals

import sys

from pre_commit.languages import helpers
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None
GREP = 'ggrep' if sys.platform == 'darwin' else 'grep'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(prefix, hook, file_args):
    # For PCRE the entry is the regular expression to match
    cmd = (GREP, '-H', '-n', '-P') + tuple(hook['args']) + (hook['entry'],)

    # Grep usually returns 0 for matches, and nonzero for non-matches so we
    # negate it here.
    return xargs(cmd, file_args, negate=True)
