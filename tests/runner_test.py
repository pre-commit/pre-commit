from __future__ import absolute_import
from __future__ import unicode_literals

import os
import os.path
from plumbum import local

import pre_commit.constants as C
from pre_commit.runner import Runner
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo


def test_init_has_no_side_effects(tmpdir):
    current_wd = os.getcwd()
    runner = Runner(tmpdir.strpath)
    assert runner.git_root == tmpdir.strpath
    assert os.getcwd() == current_wd


def test_create_sets_correct_directory(tmpdir_factory):
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        runner = Runner.create()
        assert runner.git_root == path
        assert os.getcwd() == path


def test_create_changes_to_git_root(tmpdir_factory):
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        # Change into some directory, create should set to root
        foo_path = os.path.join(path, 'foo')
        os.mkdir(foo_path)
        os.chdir(foo_path)
        assert os.getcwd() != path

        runner = Runner.create()
        assert runner.git_root == path
        assert os.getcwd() == path


def test_config_file_path():
    runner = Runner('foo/bar')
    expected_path = os.path.join('foo/bar', C.CONFIG_FILE)
    assert runner.config_file_path == expected_path


def test_repositories(tmpdir_factory, mock_out_store_directory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    runner = Runner(path)
    assert len(runner.repositories) == 1


def test_pre_commit_path():
    runner = Runner('foo/bar')
    expected_path = os.path.join('foo/bar', '.git/hooks/pre-commit')
    assert runner.pre_commit_path == expected_path


def test_cmd_runner(mock_out_store_directory):
    runner = Runner('foo/bar')
    ret = runner.cmd_runner
    assert ret.prefix_dir == os.path.join(mock_out_store_directory) + '/'
