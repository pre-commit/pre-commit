import os.path

import pytest

from pre_commit import git
from pre_commit.util import cmd_output
from testing.util import git_commit


def test_get_root_at_root(in_git_dir):
    expected = os.path.normcase(in_git_dir.strpath)
    assert os.path.normcase(git.get_root()) == expected


def test_get_root_deeper(in_git_dir):
    expected = os.path.normcase(in_git_dir.strpath)
    with in_git_dir.join('foo').ensure_dir().as_cwd():
        assert os.path.normcase(git.get_root()) == expected


def test_get_staged_files_deleted(in_git_dir):
    in_git_dir.join('test').ensure()
    cmd_output('git', 'add', 'test')
    git_commit()
    cmd_output('git', 'rm', '--cached', 'test')
    assert git.get_staged_files() == []


def test_is_not_in_merge_conflict(in_git_dir):
    assert git.is_in_merge_conflict() is False


def test_is_in_merge_conflict(in_merge_conflict):
    assert git.is_in_merge_conflict() is True


def test_is_in_merge_conflict_submodule(in_conflicting_submodule):
    assert git.is_in_merge_conflict() is True


def test_cherry_pick_conflict(in_merge_conflict):
    cmd_output('git', 'merge', '--abort')
    foo_ref = cmd_output('git', 'rev-parse', 'foo')[1].strip()
    cmd_output('git', 'cherry-pick', foo_ref, retcode=None)
    assert git.is_in_merge_conflict() is False


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
    assert ret == {'conflict_file', 'other_file'}


def test_get_conflicted_files_in_submodule(in_conflicting_submodule):
    resolve_conflict()
    assert set(git.get_conflicted_files()) == {'conflict_file'}


def test_get_conflicted_files_unstaged_files(in_merge_conflict):
    """This case no longer occurs, but it is a useful test nonetheless"""
    resolve_conflict()

    # Make unstaged file.
    with open('bar_only_file', 'w') as bar_only_file:
        bar_only_file.write('new contents!\n')

    ret = set(git.get_conflicted_files())
    assert ret == {'conflict_file'}


MERGE_MSG = b"Merge branch 'foo' into bar\n\nConflicts:\n\tconflict_file\n"
OTHER_MERGE_MSG = MERGE_MSG + b'\tother_conflict_file\n'


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


def test_get_changed_files(in_git_dir):
    git_commit()
    in_git_dir.join('a.txt').ensure()
    in_git_dir.join('b.txt').ensure()
    cmd_output('git', 'add', '.')
    git_commit()
    files = git.get_changed_files('HEAD', 'HEAD^')
    assert files == ['a.txt', 'b.txt']

    # files changed in source but not in origin should not be returned
    files = git.get_changed_files('HEAD^', 'HEAD')
    assert files == []


@pytest.mark.parametrize(
    ('s', 'expected'),
    (
        ('foo\0bar\0', ['foo', 'bar']),
        ('foo\0', ['foo']),
        ('', []),
        ('foo', ['foo']),
    ),
)
def test_zsplit(s, expected):
    assert git.zsplit(s) == expected


@pytest.fixture
def non_ascii_repo(in_git_dir):
    git_commit()
    in_git_dir.join('интервью').ensure()
    cmd_output('git', 'add', '.')
    git_commit()
    yield in_git_dir


def test_all_files_non_ascii(non_ascii_repo):
    ret = git.get_all_files()
    assert ret == ['интервью']


def test_staged_files_non_ascii(non_ascii_repo):
    non_ascii_repo.join('интервью').write('hi')
    cmd_output('git', 'add', '.')
    assert git.get_staged_files() == ['интервью']


def test_changed_files_non_ascii(non_ascii_repo):
    ret = git.get_changed_files('HEAD', 'HEAD^')
    assert ret == ['интервью']


def test_get_conflicted_files_non_ascii(in_merge_conflict):
    open('интервью', 'a').close()
    cmd_output('git', 'add', '.')
    ret = git.get_conflicted_files()
    assert ret == {'conflict_file', 'интервью'}


def test_intent_to_add(in_git_dir):
    in_git_dir.join('a').ensure()
    cmd_output('git', 'add', '--intent-to-add', 'a')

    assert git.intent_to_add_files() == ['a']


def test_status_output_with_rename(in_git_dir):
    in_git_dir.join('a').write('1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n')
    cmd_output('git', 'add', 'a')
    git_commit()
    cmd_output('git', 'mv', 'a', 'b')
    in_git_dir.join('c').ensure()
    cmd_output('git', 'add', '--intent-to-add', 'c')

    assert git.intent_to_add_files() == ['c']


def test_no_git_env():
    env = {
        'http_proxy': 'http://myproxy:80',
        'GIT_EXEC_PATH': '/some/git/exec/path',
        'GIT_SSH': '/usr/bin/ssh',
        'GIT_SSH_COMMAND': 'ssh -o',
        'GIT_DIR': '/none/shall/pass',
    }
    no_git_env = git.no_git_env(env)
    assert no_git_env == {
        'http_proxy': 'http://myproxy:80',
        'GIT_EXEC_PATH': '/some/git/exec/path',
        'GIT_SSH': '/usr/bin/ssh',
        'GIT_SSH_COMMAND': 'ssh -o',
    }
