from __future__ import unicode_literals


def file_args_to_stdin(file_args):
    return '\0'.join(list(file_args) + [''])


def run_hook(env, hook, file_args):
    return env.run(
        ' '.join(['xargs', '-0', hook['entry']] + hook['args']),
        stdin=file_args_to_stdin(file_args),
        retcode=None,
    )


class Environment(object):
    def __init__(self, repo_cmd_runner):
        self.repo_cmd_runner = repo_cmd_runner

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
