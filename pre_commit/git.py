from __future__ import unicode_literals

import logging
import os.path
import sys

from pre_commit.error_handler import FatalError
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output


logger = logging.getLogger('pre_commit')


def zsplit(s):
    s = s.strip('\0')
    if s:
        return s.split('\0')
    else:
        return []


def get_root():
    try:
        return cmd_output('git', 'rev-parse', '--show-toplevel')[1].strip()
    except CalledProcessError:
        raise FatalError(
            'git failed. Is it installed, and are you in a Git repository '
            'directory?',
        )


def get_git_dir(git_root):
    opts = ('--git-common-dir', '--git-dir')
    _, out, _ = cmd_output('git', 'rev-parse', *opts, cwd=git_root)
    for line, opt in zip(out.splitlines(), opts):
        if line != opt:  # pragma: no branch (git < 2.5)
            return os.path.normpath(os.path.join(git_root, line))
    else:
        raise AssertionError('unreachable: no git dir')


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


def get_conflicted_files():
    logger.info('Checking merge-conflict files only.')
    # Need to get the conflicted files from the MERGE_MSG because they could
    # have resolved the conflict by choosing one side or the other
    with open(os.path.join(get_git_dir('.'), 'MERGE_MSG'), 'rb') as f:
        merge_msg = f.read()
    merge_conflict_filenames = parse_merge_msg_for_conflicts(merge_msg)

    # This will get the rest of the changes made after the merge.
    # If they resolved the merge conflict by choosing a mesh of both sides
    # this will also include the conflicted files
    tree_hash = cmd_output('git', 'write-tree')[1].strip()
    merge_diff_filenames = zsplit(cmd_output(
        'git', 'diff', '--name-only', '--no-ext-diff', '-z',
        '-m', tree_hash, 'HEAD', 'MERGE_HEAD',
    )[1])
    return set(merge_conflict_filenames) | set(merge_diff_filenames)


def get_staged_files():
    return zsplit(cmd_output(
        'git', 'diff', '--staged', '--name-only', '--no-ext-diff', '-z',
        # Everything except for D
        '--diff-filter=ACMRTUXB',
    )[1])


def get_all_files():
    return zsplit(cmd_output('git', 'ls-files', '-z')[1])


def get_changed_files(new, old):
    return zsplit(cmd_output(
        'git', 'diff', '--name-only', '--no-ext-diff', '-z',
        '{}...{}'.format(old, new),
    )[1])


def head_rev(remote):
    _, out, _ = cmd_output('git', 'ls-remote', '--exit-code', remote, 'HEAD')
    return out.split()[0]


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
                    exe_type[is_cygwin_python], exe_type[is_cygwin_git],
                ),
            )
