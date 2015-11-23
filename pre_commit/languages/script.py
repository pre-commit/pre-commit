from __future__ import unicode_literals

from pre_commit.languages.helpers import file_args_to_stdin


ENVIRONMENT_DIR = None


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=None,
):
    """Installation for script type is a noop."""
    raise AssertionError('Cannot install script repo.')


def run_hook(repo_cmd_runner, hook, file_args):
    return repo_cmd_runner.run(
        ['xargs', '-0', '{{prefix}}{0}'.format(hook['entry'])] + hook['args'],
        stdin=file_args_to_stdin(file_args),
        retcode=None,
        encoding=None,
    )
