
from plumbum import local


def run_hook(env, hook, file_args):
    return env.run(
        ' '.join([hook['entry']] + hook.get('args', []) + list(file_args)),
        retcode=None,
    )
    return env.run(
        ' '.join(['xargs |', hook['entry']] + hook.get('args', [])),
        retcode=None,
        stdin='\n'.join(file_args) + '\n',
    )


class Environment(object):
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
        return local['bash'][
            '-c',
            ' '.join([self.env_prefix, cmd])
        ].run(**kwargs)
