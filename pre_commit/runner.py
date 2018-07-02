from __future__ import unicode_literals

import os.path

from cached_property import cached_property

from pre_commit import git
from pre_commit.clientlib import load_config


class Runner(object):
    """A `Runner` represents the execution context of the hooks.  Notably the
    repository under test.
    """

    def __init__(self, git_root, config_file):
        self.git_root = git_root
        self.config_file = config_file

    @classmethod
    def create(cls, config_file):
        """Creates a Runner by doing the following:
            - Finds the root of the current git repository
            - chdir to that directory
        """
        root = git.get_root()
        os.chdir(root)
        return cls(root, config_file)

    @property
    def config_file_path(self):
        return os.path.join(self.git_root, self.config_file)

    @cached_property
    def config(self):
        return load_config(self.config_file_path)

    def get_hook_path(self, hook_type):
        return os.path.join(git.get_git_dir(self.git_root), 'hooks', hook_type)
