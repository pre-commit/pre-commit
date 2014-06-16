from __future__ import unicode_literals

import shlex


ENVIRONMENT_DIR = None


def install_environment(repo_cmd_runner, version='default'):
    """Installation for system type is a noop."""


def run_hook(repo_cmd_runner, hook, file_args):
    return repo_cmd_runner.run(
        ['xargs'] + shlex.split(hook['entry']) + hook['args'],
        # TODO: this is duplicated in pre_commit/languages/helpers.py
        stdin='\n'.join(list(file_args) + ['']),
        retcode=None,
    )
