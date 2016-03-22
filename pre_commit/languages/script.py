from __future__ import unicode_literals

from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    """Installation for script type is a noop."""
    raise AssertionError('Cannot install script repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    return xargs(
        (repo_cmd_runner.prefix_dir + hook['entry'],) + tuple(hook['args']),
        file_args,
    )
