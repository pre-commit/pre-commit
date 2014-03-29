
import os
import os.path
import subprocess


def _replace_cmd(cmd, **kwargs):
    return [part.format(**kwargs) for part in cmd]


class PrefixedCommandRunner(object):
    """A PrefixedCommandRunner allows you to run subprocess commands with
    comand substitution.

    For instance:
        PrefixedCommandRunner('/tmp/foo').run(['{prefix}foo.sh', 'bar', 'baz'])

    will run ['/tmpl/foo/foo.sh', 'bar', 'baz']
    """
    def __init__(self, prefix_dir, popen=subprocess.Popen):
        self.prefix_dir = prefix_dir.rstrip(os.sep) + os.sep
        self.__popen = popen

    def run(self, cmd, stdin=None):
        replaced_cmd = _replace_cmd(cmd, prefix=self.prefix_dir)
        proc = self.__popen(
            replaced_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = proc.communicate(stdin)

        return proc.returncode, stdout, stderr

    def path(self, path_end):
        path = os.path.join(self.prefix_dir, path_end)
        return os.path.normpath(path)

    @classmethod
    def from_command_runner(cls, command_runner, path_end):
        """Constructs a new command runner from an existing one by appending
        `path_end` to the command runner's prefix directory.
        """
        return cls(command_runner.path(path_end), popen=command_runner.__popen)
