
import subprocess


def run_hook(env, hook, file_args):
    return env.run(
        ' '.join(['xargs', hook['entry']] + hook.get('args', [])),
        stdin='\n'.join(list(file_args) + ['']),
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

    def run(self, cmd, stdin=None):
        """Returns (returncode, stdout, stderr)."""
        proc = subprocess.Popen(
            ['bash', '-c', ' '.join([self.env_prefix, cmd])],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(stdin)

        return proc.returncode, stdout, stderr
