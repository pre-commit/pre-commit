from __future__ import unicode_literals

import pipes


def environment_dir(ENVIRONMENT_DIR, language_version):
    if ENVIRONMENT_DIR is None:
        return None
    else:
        return '{0}-{1}'.format(ENVIRONMENT_DIR, language_version)


def file_args_to_stdin(file_args):
    return '\0'.join(list(file_args) + [''])


def run_hook(env, hook, file_args):
    quoted_args = [pipes.quote(arg) for arg in hook['args']]
    return env.run(
        # Use -s 4000 (slightly less than posix mandated minimum)
        # This is to prevent "xargs: ... Bad file number" on windows
        ' '.join(['xargs', '-0', '-s4000', hook['entry']] + quoted_args),
        stdin=file_args_to_stdin(file_args),
        retcode=None,
        encoding=None,
    )


class Environment(object):
    def __init__(self, repo_cmd_runner, language_version):
        self.repo_cmd_runner = repo_cmd_runner
        self.language_version = language_version

    @property
    def env_prefix(self):
        """env_prefix is a value that is prefixed to the command that is run.

        Usually this is to source a virtualenv, etc.

        Commands basically end up looking like:

        bash -c '{env_prefix} {cmd}'

        so you'll often want to end your prefix with &&
        """
        raise NotImplementedError

    def run(self, cmd, **kwargs):
        """Returns (returncode, stdout, stderr)."""
        return self.repo_cmd_runner.run(
            ['bash', '-c', ' '.join([self.env_prefix, cmd])], **kwargs
        )
