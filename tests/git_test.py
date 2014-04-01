
import pytest
from plumbum import local

from pre_commit import git


def test_get_root(empty_git_dir):
    assert git.get_root() == empty_git_dir

    foo = local.path('foo')
    foo.mkdir()

    with local.cwd(foo):
        assert git.get_root() == empty_git_dir


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
    ret = get_files_matching_func('^.*\.py$', '^$')
    assert ret == set([
        'pre_commit/run.py',
        'pre_commit/git.py',
    ])


def test_does_search_instead_of_match(get_files_matching_func):
    ret = get_files_matching_func('\.yaml$', '^$')
    assert ret == set(['hooks.yaml'])


def test_does_not_include_deleted_fileS(get_files_matching_func):
    ret = get_files_matching_func('exist.py', '^$')
    assert ret == set()


def test_exclude_removes_files(get_files_matching_func):
    ret = get_files_matching_func('', '\.py$')
    assert ret == set(['hooks.yaml'])
