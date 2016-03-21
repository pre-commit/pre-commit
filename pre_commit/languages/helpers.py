from __future__ import unicode_literals

from pre_commit.util import cmd_output


def run_setup_cmd(runner, cmd):
    cmd_output(*cmd, cwd=runner.prefix_dir, encoding=None)


def environment_dir(ENVIRONMENT_DIR, language_version):
    if ENVIRONMENT_DIR is None:
        return None
    else:
        return '{0}-{1}'.format(ENVIRONMENT_DIR, language_version)


def file_args_to_stdin(file_args):
    return '\0'.join(list(file_args) + [''])


def run_hook(cmd_args, file_args):
    return cmd_output(
        # Use -s 4000 (slightly less than posix mandated minimum)
        # This is to prevent "xargs: ... Bad file number" on windows
        'xargs', '-0', '-s4000', *cmd_args,
        stdin=file_args_to_stdin(file_args),
        retcode=None,
        encoding=None
    )
