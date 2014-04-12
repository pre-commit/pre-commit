import os
import os.path
import pytest

import pre_commit.constants as C
from pre_commit.runner import Runner


def test_init_has_no_side_effects(tmpdir):
    current_wd = os.getcwd()
    runner = Runner(tmpdir.strpath)
    assert runner.git_root == tmpdir.strpath
    assert os.getcwd() == current_wd


def test_create_sets_correct_directory(empty_git_dir):
    runner = Runner.create()
    assert runner.git_root == empty_git_dir
    assert os.getcwd() == empty_git_dir


@pytest.yield_fixture
def git_dir_with_directory(empty_git_dir):
    os.mkdir('foo')
    yield empty_git_dir


def test_changes_to_root_of_git_dir(git_dir_with_directory):
    os.chdir('foo')
    assert os.getcwd() != git_dir_with_directory
    runner = Runner.create()
    assert runner.git_root == git_dir_with_directory
    assert os.getcwd() == git_dir_with_directory


def test_hooks_workspace_path():
    runner = Runner('foo/bar')
    expected_path = os.path.join('foo/bar', C.HOOKS_WORKSPACE)
    assert runner.hooks_workspace_path == expected_path


def test_config_file_path():
    runner = Runner('foo/bar')
    expected_path = os.path.join('foo/bar', C.CONFIG_FILE)
    assert runner.config_file_path == expected_path


def test_repositories(consumer_repo):
    runner = Runner(consumer_repo)
    assert len(runner.repositories) == 2
    assert [repo.repo_url for repo in runner.repositories] == [
        'git@github.com:pre-commit/pre-commit-hooks',
        'git@github.com:pre-commit/pre-commit',
    ]


def test_pre_commit_path():
    runner = Runner('foo/bar')
    expected_path = os.path.join('foo/bar', '.git/hooks/pre-commit')
    assert runner.pre_commit_path == expected_path


def test_cmd_runner():
    runner = Runner('foo/bar')
    ret = runner.cmd_runner
    assert ret.prefix_dir == os.path.join('foo/bar', C.HOOKS_WORKSPACE) + '/'
