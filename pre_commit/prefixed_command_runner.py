from __future__ import unicode_literals

import os
import os.path
import subprocess


class CalledProcessError(RuntimeError):
    def __init__(self, returncode, cmd, expected_returncode, output=None):
        super(CalledProcessError, self).__init__(
            returncode, cmd, expected_returncode, output,
        )
        self.returncode = returncode
        self.cmd = cmd
        self.expected_returncode = expected_returncode
        self.output = output

    def __str__(self):
        return (
            'Command: {0!r}\n'
            'Return code: {1}\n'
            'Expected return code: {2}\n'
            'Output: {3!r}\n'.format(
                self.cmd,
                self.returncode,
                self.expected_returncode,
                self.output,
            )
        )


def _replace_cmd(cmd, **kwargs):
    return [part.format(**kwargs) for part in cmd]


class PrefixedCommandRunner(object):
    """A PrefixedCommandRunner allows you to run subprocess commands with
    comand substitution.

    For instance:
        PrefixedCommandRunner('/tmp/foo').run(['{prefix}foo.sh', 'bar', 'baz'])

    will run ['/tmp/foo/foo.sh', 'bar', 'baz']
    """
    def __init__(
            self,
            prefix_dir,
            popen=subprocess.Popen,
            makedirs=os.makedirs
    ):
        self.prefix_dir = prefix_dir.rstrip(os.sep) + os.sep
        self.__popen = popen
        self.__makedirs = makedirs

    def _create_path_if_not_exists(self):
        if not os.path.exists(self.prefix_dir):
            self.__makedirs(self.prefix_dir)

    def run(self, cmd, retcode=0, stdin=None, encoding='UTF-8', **kwargs):
        popen_kwargs = {
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
        }
        if stdin is not None:
            stdin = stdin.encode('UTF-8')

        popen_kwargs.update(kwargs)
        self._create_path_if_not_exists()
        replaced_cmd = _replace_cmd(cmd, prefix=self.prefix_dir)
        proc = self.__popen(replaced_cmd, **popen_kwargs)
        stdout, stderr = proc.communicate(stdin)
        if encoding is not None:
            stdout = stdout.decode(encoding)
        if encoding is not None:
            stderr = stderr.decode(encoding)
        returncode = proc.returncode

        if retcode is not None and retcode != returncode:
            raise CalledProcessError(
                returncode, replaced_cmd, retcode, output=(stdout, stderr),
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
        return cls(
            command_runner.path(path_end),
            popen=command_runner.__popen,
            makedirs=command_runner.__makedirs,
        )
