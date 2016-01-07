from __future__ import unicode_literals

import functools
import logging
import os
import os.path
import re

from pre_commit.errors import FatalError
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from pre_commit.util import memoize_by_cwd

GIT_MODE_FILE = 0o100644
GIT_MODE_EXECUTABLE = 0o100755
GIT_MODE_SYMLINK = 0o120000
GIT_MODE_SUBMODULE = 0o160000


logger = logging.getLogger('pre_commit')


def get_root():
    try:
        return cmd_output('git', 'rev-parse', '--show-toplevel')[1].strip()
    except CalledProcessError:
        raise FatalError(
            'Called from outside of the gits.  Please cd to a git repository.'
        )


def get_git_dir(git_root):
    return os.path.normpath(os.path.join(
        git_root,
        cmd_output('git', 'rev-parse', '--git-dir', cwd=git_root)[1].strip(),
    ))


def is_in_merge_conflict():
    git_dir = get_git_dir('.')
    return (
        os.path.exists(os.path.join(git_dir, 'MERGE_MSG')) and
        os.path.exists(os.path.join(git_dir, 'MERGE_HEAD'))
    )


def parse_merge_msg_for_conflicts(merge_msg):
    # Conflicted files start with tabs
    return [
        line.lstrip('#').strip()
        for line in merge_msg.splitlines()
        # '#\t' for git 2.4.1
        if line.startswith(('\t', '#\t'))
    ]


@memoize_by_cwd
def get_conflicted_files():
    """Return a list of file names and types for conflicted files."""
    logger.info('Checking merge-conflict files only.')
    # Need to get the conflicted files from the MERGE_MSG because they could
    # have resolved the conflict by choosing one side or the other
    merge_msg = open(os.path.join(get_git_dir('.'), 'MERGE_MSG')).read()
    merge_conflict_filenames = parse_merge_msg_for_conflicts(merge_msg)

    # This will get the rest of the changes made after the merge.
    # If they resolved the merge conflict by choosing a mesh of both sides
    # this will also include the conflicted files
    tree_hash = cmd_output('git', 'write-tree')[1].strip()
    merge_diff_filenames = cmd_output(
        'git', 'diff', '-m', tree_hash, 'HEAD', 'MERGE_HEAD', '--name-only',
    )[1].splitlines()

    return [
        (path, get_git_type_for_file(path))
        for path
        in set(merge_conflict_filenames) | set(merge_diff_filenames)
    ]


def get_git_type_for_file(path):
    """Return the git type of a file which is in this git repository.

    Because the file is in this git repository, we can use `git ls-files` to
    read its type directly.
    """
    # TODO: call this function once with a list of paths for more speed?
    _, mode = _parse_git_ls_line(
        cmd_output('git', 'ls-files', '--stage', '--', path)[1],
    )
    return mode


def guess_git_type_for_file(path):
    """Return a guessed git type of a file which is not in this git repository.

    Because the file isn't in git, we must guess the file type. This is
    necessary when using `pre-commit run` or `pre-commit identify` and listing
    files (which might not be in a repo).
    """
    if os.path.islink(path):
        return GIT_MODE_SYMLINK
    elif os.path.isfile(path):
        # determine if executable
        if os.access(path, os.X_OK):
            return GIT_MODE_EXECUTABLE
        else:
            return GIT_MODE_FILE
    elif os.path.isdir(path):
        # git doesn't track directories, so if it *is* one, it's a submodule
        return GIT_MODE_SUBMODULE
    else:
        raise ValueError('Unable to determine type of `{0}`'.format(path))


@memoize_by_cwd
def get_staged_files():
    """Return a list of paths in the repo which have been added/modified."""
    return [
        (path, get_git_type_for_file(path))
        for path
        in cmd_output(
            'git', 'diff',
            '--diff-filter=ACMRTUXB',  # all types except D ("Deleted")
            '--staged',
            '--name-only',
        )[1].splitlines()
    ]


# The output format of the command is:
# [file mode] [object hash] [stage number]\t[file path]
# (We only care about the mode and path.)
_split_git_ls_line_regex = re.compile('^([0-7]{6}) [0-9a-f]{40} [0-9]+\t(.+)$')


def _parse_git_ls_line(line):
    """Split a line of `git ls-files` into a tuple (path, type)."""
    match = _split_git_ls_line_regex.match(line)
    return match.group(2), int(match.group(1), 8)


@memoize_by_cwd
def get_all_files():
    """Return a list of all files (and their types) in the repository.

    :return: list of (path, type) tuples
    """
    return [
        _parse_git_ls_line(line)
        for line in cmd_output('git', 'ls-files', '--stage')[1].splitlines()
    ]


def get_files_matching(all_file_list_strategy):
    @functools.wraps(all_file_list_strategy)
    @memoize_by_cwd
    def wrapper(include_expr, exclude_expr, types):
        # TODO: how to avoid this?
        from pre_commit.file_classifier.classifier import classify

        include_regex = re.compile(include_expr)
        exclude_regex = re.compile(exclude_expr)
        return set(
            filename
            for filename, mode in all_file_list_strategy()
            if (
                include_regex.search(filename) and
                not exclude_regex.search(filename) and
                os.path.lexists(filename) and
                classify(filename, mode).intersection(types)
            )
        )
    return wrapper


get_staged_files_matching = get_files_matching(get_staged_files)
get_all_files_matching = get_files_matching(get_all_files)
get_conflicted_files_matching = get_files_matching(get_conflicted_files)
