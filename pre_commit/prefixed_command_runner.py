from __future__ import unicode_literals

import os
import os.path
import subprocess

from pre_commit.util import cmd_output


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

    def run(self, cmd, **kwargs):
        self._create_path_if_not_exists()
        replaced_cmd = [
            part.replace('{prefix}', self.prefix_dir) for part in cmd
        ]
        return cmd_output(*replaced_cmd, __popen=self.__popen, **kwargs)

    def path(self, *parts):
        path = os.path.join(self.prefix_dir, *parts)
        return os.path.normpath(path)

    def exists(self, *parts):
        return os.path.exists(self.path(*parts))

    def star(self, end):
        return tuple(
            path for path in os.listdir(self.prefix_dir) if path.endswith(end)
        )
