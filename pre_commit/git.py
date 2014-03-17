import functools
import os
import pkg_resources
import re
from plumbum import local

from pre_commit.util import memoize_by_cwd


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
def get_all_files():
    return local['git']['ls-files']().splitlines()


def get_files_matching(all_file_list_strategy):
    @functools.wraps(all_file_list_strategy)
    @memoize_by_cwd
    def wrapper(expr):
        regex = re.compile(expr)
        return set(
            filename
            for filename in all_file_list_strategy()
            if regex.search(filename)
        )
    return wrapper



get_staged_files_matching = get_files_matching(get_staged_files)
get_all_files_matching = get_files_matching(get_all_files)
