import os
import pkg_resources
from plumbum import local

from pre_commit.util import memoize_by_cwd


@memoize_by_cwd
def get_root():
    return local['git']['rev-parse', '--show-toplevel']().strip()


@memoize_by_cwd
def get_pre_commit_path():
    return os.path.join(get_root(), '.git/hooks/pre-commit')


def create_pre_commit():
    path = get_pre_commit_path()
    pre_commit_file = pkg_resources.resource_filename('pre_commit', 'resources/pre-commit.sh')
    local.path(path).write(local.path(pre_commit_file).read())


def remove_pre_commit():
    local.path(get_pre_commit_path()).delete()


def get_head_sha(git_repo_path):
    with local.cwd(git_repo_path):
        return (local['git']['rev-parse', 'HEAD'])().strip()
