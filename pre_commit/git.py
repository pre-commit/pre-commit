import os
import re
import pkg_resources
from plumbum import local

from pre_commit.util import memoize_by_cwd


def _get_root_original():
    return local['git']['rev-parse', '--show-toplevel']().strip()

def _get_root_new():
    path = os.getcwd()
    while len(path) > 1:
        if os.path.exists(os.path.join(path, '.git')):
            return path
        else:
            path = os.path.normpath(os.path.join(path, '../'))
    raise AssertionError('called from outside of the gits')


@memoize_by_cwd
def get_root():
    return _get_root_new()
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
        return local['git']['rev-parse', 'HEAD']().strip()


@memoize_by_cwd
def get_staged_files():
    return local['git']['diff', '--staged', '--name-only']().splitlines()


@memoize_by_cwd
def get_staged_files_matching(expr):
    regex = re.compile(expr)
    return set(
        filename for filename in get_staged_files() if regex.search(filename)
    )


@memoize_by_cwd
def get_all_files():
    return local['git']['ls-files']().splitlines()


# Smell: this is duplicated above
@memoize_by_cwd
def get_all_files_matching(expr):
    regex = re.compile(expr)
    return set(
        filename for filename in get_all_files() if regex.search(filename)
    )