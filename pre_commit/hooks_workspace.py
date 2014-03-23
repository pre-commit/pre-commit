
import contextlib
import os.path
from plumbum import local

import pre_commit.constants as C
from pre_commit import git


def get_pre_commit_dir_path():
    return os.path.join(git.get_root(), C.HOOKS_WORKSPACE)


@contextlib.contextmanager
def in_hooks_workspace():
    """Change into the hooks workspace.  If it does not exist create it."""
    if not os.path.exists(get_pre_commit_dir_path()):
        local.path(get_pre_commit_dir_path()).mkdir()

    with local.cwd(get_pre_commit_dir_path()):
        yield
