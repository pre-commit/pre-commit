import functools
import os
import os.path
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
    def wrapper(include_expr, exclude_expr):
        include_regex = re.compile(include_expr)
        exclude_regex = re.compile(exclude_expr)
        return set(filter(os.path.exists, (
            filename
            for filename in all_file_list_strategy()
            if (
                include_regex.search(filename) and
                not exclude_regex.search(filename)
            )
        )))
    return wrapper


get_staged_files_matching = get_files_matching(get_staged_files)
get_all_files_matching = get_files_matching(get_all_files)
