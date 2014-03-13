
import os
import pytest

from plumbum import local
from pre_commit import git


@pytest.yield_fixture
def empty_git_dir(tmpdir):
    with local.cwd(tmpdir.strpath):
        local['git']['init']()
        yield tmpdir.strpath


@pytest.yield_fixture
def dummy_git_repo(empty_git_dir):
    local['touch']['dummy']()
    local['git']['add', 'dummy']()
    local['git']['commit', '-m', 'dummy commit']()

    yield empty_git_dir

def test_get_root(empty_git_dir):
    assert git.get_root() == empty_git_dir

    foo = local.path('foo')
    foo.mkdir()

    with local.cwd(foo):
        assert git.get_root() == empty_git_dir


def test_get_pre_commit_path(empty_git_dir):
    assert git.get_pre_commit_path() == '{0}/.git/hooks/pre-commit'.format(empty_git_dir)


def test_create_pre_commit(empty_git_dir):
    git.create_pre_commit()
    assert len(open(git.get_pre_commit_path(), 'r').read()) > 0


def test_remove_pre_commit(empty_git_dir):
    git.remove_pre_commit()

    assert not os.path.exists(git.get_pre_commit_path())

    git.create_pre_commit()
    git.remove_pre_commit()

    assert not os.path.exists(git.get_pre_commit_path())


def test_create_repo_in_env(empty_git_dir, dummy_git_repo):
    git.create_repo_in_env('pre-commit', dummy_git_repo)