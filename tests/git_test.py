
import os
import pytest
from plumbum import local

from pre_commit import git


def test_get_root(empty_git_dir):
    assert git.get_root() == empty_git_dir

    foo = local.path('foo')
    foo.mkdir()

    with local.cwd(foo):
        assert git.get_root() == empty_git_dir


def test_get_pre_commit_path(empty_git_dir):
    assert git.get_pre_commit_path() == '{0}/.git/hooks/pre-commit'.format(
        empty_git_dir,
    )


def test_create_pre_commit(empty_git_dir):
    git.create_pre_commit()
    assert len(open(git.get_pre_commit_path(), 'r').read()) > 0


def test_remove_pre_commit(empty_git_dir):
    git.remove_pre_commit()

    assert not os.path.exists(git.get_pre_commit_path())

    git.create_pre_commit()
    git.remove_pre_commit()

    assert not os.path.exists(git.get_pre_commit_path())


@pytest.fixture
def get_files_matching_func():
    def get_filenames():
        return (
            'foo.py',
            'bar/baz.py',
            'tests/baz_test.py',
            'manifest.yaml',
        )

    return git.get_files_matching(get_filenames)


def test_get_files_matching_base(get_files_matching_func):
    ret = get_files_matching_func('')
    assert ret == set([
        'foo.py',
        'bar/baz.py',
        'tests/baz_test.py',
        'manifest.yaml',
    ])


def test_get_files_matching_total_match(get_files_matching_func):
    ret = get_files_matching_func('^.*\.py$')
    assert ret == set([
        'foo.py',
        'bar/baz.py',
        'tests/baz_test.py',
    ])


def test_does_search_instead_of_match(get_files_matching_func):
    ret = get_files_matching_func('\.yaml$')
    assert ret == set(['manifest.yaml'])
