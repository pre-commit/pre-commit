from __future__ import unicode_literals

import functools
import logging
import os.path
import re
import sys

from pre_commit.errors import FatalError
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from pre_commit.util import memoize_by_cwd


logger = logging.getLogger('pre_commit')


def get_root():
    try:
        return cmd_output('git', 'rev-parse', '--show-toplevel')[1].strip()
    except CalledProcessError:
        raise FatalError(
            'git failed. Is it installed, and are you in a Git repository '
            'directory?',
        )


def get_git_dir(git_root):
    return os.path.normpath(os.path.join(
        git_root,
        cmd_output('git', 'rev-parse', '--git-dir', cwd=git_root)[1].strip(),
    ))


def get_remote_url(git_root):
    ret = cmd_output('git', 'config', 'remote.origin.url', cwd=git_root)[1]
    return ret.strip()


def is_in_merge_conflict():
    git_dir = get_git_dir('.')
    return (
        os.path.exists(os.path.join(git_dir, 'MERGE_MSG')) and
        os.path.exists(os.path.join(git_dir, 'MERGE_HEAD'))
    )


def parse_merge_msg_for_conflicts(merge_msg):
    # Conflicted files start with tabs
    return [
        line.lstrip(b'#').strip().decode('UTF-8')
        for line in merge_msg.splitlines()
        # '#\t' for git 2.4.1
        if line.startswith((b'\t', b'#\t'))
    ]


@memoize_by_cwd
def get_conflicted_files():
    logger.info('Checking merge-conflict files only.')
    # Need to get the conflicted files from the MERGE_MSG because they could
    # have resolved the conflict by choosing one side or the other
    merge_msg = open(os.path.join(get_git_dir('.'), 'MERGE_MSG'), 'rb').read()
    merge_conflict_filenames = parse_merge_msg_for_conflicts(merge_msg)

    # This will get the rest of the changes made after the merge.
    # If they resolved the merge conflict by choosing a mesh of both sides
    # this will also include the conflicted files
    tree_hash = cmd_output('git', 'write-tree')[1].strip()
    merge_diff_filenames = cmd_output(
        'git', 'diff', '--no-ext-diff',
        '-m', tree_hash, 'HEAD', 'MERGE_HEAD', '--name-only',
    )[1].splitlines()
    return set(merge_conflict_filenames) | set(merge_diff_filenames)


@memoize_by_cwd
def get_staged_files():
    return cmd_output(
        'git', 'diff', '--staged', '--name-only', '--no-ext-diff',
        # Everything except for D
        '--diff-filter=ACMRTUXB',
    )[1].splitlines()


@memoize_by_cwd
def get_all_files():
    return cmd_output('git', 'ls-files')[1].splitlines()


def get_files_matching(all_file_list_strategy):
    @functools.wraps(all_file_list_strategy)
    @memoize_by_cwd
    def wrapper(include_expr, exclude_expr):
        include_regex = re.compile(include_expr)
        exclude_regex = re.compile(exclude_expr)
        return {
            filename
            for filename in all_file_list_strategy()
            if (
                include_regex.search(filename) and
                not exclude_regex.search(filename) and
                os.path.lexists(filename)
            )
        }
    return wrapper


get_staged_files_matching = get_files_matching(get_staged_files)
get_all_files_matching = get_files_matching(get_all_files)
get_conflicted_files_matching = get_files_matching(get_conflicted_files)


def check_for_cygwin_mismatch():
    """See https://github.com/pre-commit/pre-commit/issues/354"""
    if sys.platform in ('cygwin', 'win32'):  # pragma: no cover (windows)
        is_cygwin_python = sys.platform == 'cygwin'
        toplevel = cmd_output('git', 'rev-parse', '--show-toplevel')[1]
        is_cygwin_git = toplevel.startswith('/')

        if is_cygwin_python ^ is_cygwin_git:
            exe_type = {True: '(cygwin)', False: '(windows)'}
            logger.warn(
                'pre-commit has detected a mix of cygwin python / git\n'
                'This combination is not supported, it is likely you will '
                'receive an error later in the program.\n'
                'Make sure to use cygwin git+python while using cygwin\n'
                'These can be installed through the cygwin installer.\n'
                ' - python {}\n'
                ' - git {}\n'.format(
                    exe_type[is_cygwin_python],
                    exe_type[is_cygwin_git],
                ),
            )
