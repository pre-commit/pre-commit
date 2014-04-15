import pytest
from plumbum import local

from pre_commit import git


def test_get_root(empty_git_dir):
    assert git.get_root() == empty_git_dir

    foo = local.path('foo')
    foo.mkdir()

    with local.cwd(foo):
        assert git.get_root() == empty_git_dir


def test_is_in_merge_conflict(empty_git_dir):
    assert git.is_in_merge_conflict() is False


def test_is_not_in_merge_conflict(in_merge_conflict):
    assert git.is_in_merge_conflict() is True


@pytest.fixture
def get_files_matching_func():
    def get_filenames():
        return (
            'pre_commit/run.py',
            'pre_commit/git.py',
            'im_a_file_that_doesnt_exist.py',
            'hooks.yaml',
        )

    return git.get_files_matching(get_filenames)


def test_get_files_matching_base(get_files_matching_func):
    ret = get_files_matching_func('', '^$')
    assert ret == set([
        'pre_commit/run.py',
        'pre_commit/git.py',
        'hooks.yaml',
    ])


def test_get_files_matching_total_match(get_files_matching_func):
    ret = get_files_matching_func('^.*\\.py$', '^$')
    assert ret == set([
        'pre_commit/run.py',
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
    local['git']['add', 'conflict_file']()


def test_get_conflicted_files(in_merge_conflict):
    resolve_conflict()
    with open('other_file', 'w') as other_file:
        other_file.write('oh hai')
    local['git']['add', 'other_file']()

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
