from __future__ import unicode_literals

from pre_commit.languages import helpers
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def install_environment(repo_cmd_runner, version, additional_dependencies):
    """Installation for script type is a noop."""
    raise AssertionError('Cannot install script repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    cmd = helpers.to_cmd(hook)
    cmd = (repo_cmd_runner.prefix_dir + cmd[0],) + cmd[1:]
    return xargs(cmd, file_args)
