
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
    def __init__(self, prefix_dir, popen=subprocess.Popen, makedirs=os.makedirs):
        self.prefix_dir = prefix_dir.rstrip(os.sep) + os.sep
        self.__popen = popen
        self.__makedirs = makedirs

    def _create_path_if_not_exists(self):
        if not os.path.exists(self.prefix_dir):
            self.__makedirs(self.prefix_dir)

    def run(self, cmd, retcode=0, stdin=None, **kwargs):
        self._create_path_if_not_exists()
        replaced_cmd = _replace_cmd(cmd, prefix=self.prefix_dir)
        proc = self.__popen(
            replaced_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs
        )
        stdout, stderr = proc.communicate(stdin)
        returncode = proc.returncode

        if retcode is not None and retcode != returncode:
            raise subprocess.CalledProcessError(
                returncode, replaced_cmd, output=(stdout, stderr),
            )

        return proc.returncode, stdout, stderr

    def path(self, *parts):
        path = os.path.join(self.prefix_dir, *parts)
        return os.path.normpath(path)

    def exists(self, *parts):
        return os.path.exists(self.path(*parts))

    @classmethod
    def from_command_runner(cls, command_runner, path_end):
        """Constructs a new command runner from an existing one by appending
        `path_end` to the command runner's prefix directory.
        """
        return cls(command_runner.path(path_end), popen=command_runner.__popen)
