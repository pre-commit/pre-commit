from __future__ import absolute_import
from __future__ import unicode_literals

import os.path

import pytest

from pre_commit import git
from pre_commit.errors import FatalError
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.fixtures import git_dir


def test_get_root_at_root(tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        assert git.get_root() == path


def test_get_root_deeper(tempdir_factory):
    path = git_dir(tempdir_factory)

    foo_path = os.path.join(path, 'foo')
    os.mkdir(foo_path)
    with cwd(foo_path):
        assert git.get_root() == path


def test_get_root_not_git_dir(tempdir_factory):
    with cwd(tempdir_factory.get()):
        with pytest.raises(FatalError):
            git.get_root()


def test_is_not_in_merge_conflict(tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        assert git.is_in_merge_conflict() is False


def test_is_in_merge_conflict(in_merge_conflict):
    assert git.is_in_merge_conflict() is True


def test_cherry_pick_conflict(in_merge_conflict):
    cmd_output('git', 'merge', '--abort')
    foo_ref = cmd_output('git', 'rev-parse', 'foo')[1].strip()
    cmd_output('git', 'cherry-pick', foo_ref, retcode=None)
    assert git.is_in_merge_conflict() is False


@pytest.fixture
def get_files_matching_func():
    def get_filenames():
        return (
            'pre_commit/main.py',
            'pre_commit/git.py',
            'im_a_file_that_doesnt_exist.py',
            'hooks.yaml',
        )

    return git.get_files_matching(get_filenames)


def test_get_files_matching_base(get_files_matching_func):
    ret = get_files_matching_func('', '^$')
    assert ret == set([
        'pre_commit/main.py',
        'pre_commit/git.py',
        'hooks.yaml',
    ])


def test_get_files_matching_total_match(get_files_matching_func):
    ret = get_files_matching_func('^.*\\.py$', '^$')
    assert ret == set([
        'pre_commit/main.py',
        'pre_commit/git.py',
    ])


def test_does_search_instead_of_match(get_files_matching_func):
    ret = get_files_matching_func('\\.yaml$', '^$')
    assert ret == set(['hooks.yaml'])


def test_does_not_include_deleted_fileS(get_files_matching_func):
    ret = get_files_matching_func('exist.py', '^$')
    assert ret == set()


def test_exclude_removes_files(get_files_matching_func):
    ret = get_files_matching_func('', '\\.py$')
    assert ret == set(['hooks.yaml'])


def resolve_conflict():
    with open('conflict_file', 'w') as conflicted_file:
        conflicted_file.write('herp\nderp\n')
    cmd_output('git', 'add', 'conflict_file')


def test_get_conflicted_files(in_merge_conflict):
    resolve_conflict()
    with open('other_file', 'w') as other_file:
        other_file.write('oh hai')
    cmd_output('git', 'add', 'other_file')

    ret = set(git.get_conflicted_files())
    assert ret == set(('conflict_file', 'other_file'))


def test_get_conflicted_files_unstaged_files(in_merge_conflict):
    # If they for whatever reason did pre-commit run --no-stash during a
    # conflict
    resolve_conflict()

    # Make unstaged file.
    with open('bar_only_file', 'w') as bar_only_file:
        bar_only_file.write('new contents!\n')

    ret = set(git.get_conflicted_files())
    assert ret == set(('conflict_file',))


MERGE_MSG = "Merge branch 'foo' into bar\n\nConflicts:\n\tconflict_file\n"
OTHER_MERGE_MSG = MERGE_MSG + '\tother_conflict_file\n'


@pytest.mark.parametrize(
    ('input', 'expected_output'),
    (
        (MERGE_MSG, ['conflict_file']),
        (OTHER_MERGE_MSG, ['conflict_file', 'other_conflict_file']),
    ),
)
def test_parse_merge_msg_for_conflicts(input, expected_output):
    ret = git.parse_merge_msg_for_conflicts(input)
    assert ret == expected_output
