from __future__ import absolute_import
from __future__ import unicode_literals

import os.path

import pre_commit.constants as C
from pre_commit.runner import Runner
from testing.fixtures import git_dir
from testing.util import cwd


def test_init_has_no_side_effects(tmpdir):
    current_wd = os.getcwd()
    runner = Runner(tmpdir.strpath, C.CONFIG_FILE)
    assert runner.git_root == tmpdir.strpath
    assert os.getcwd() == current_wd


def test_create_sets_correct_directory(tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        runner = Runner.create(C.CONFIG_FILE)
        assert os.path.normcase(runner.git_root) == os.path.normcase(path)
        assert os.path.normcase(os.getcwd()) == os.path.normcase(path)


def test_create_changes_to_git_root(tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        # Change into some directory, create should set to root
        foo_path = os.path.join(path, 'foo')
        os.mkdir(foo_path)
        os.chdir(foo_path)
        assert os.getcwd() != path

        runner = Runner.create(C.CONFIG_FILE)
        assert os.path.normcase(runner.git_root) == os.path.normcase(path)
        assert os.path.normcase(os.getcwd()) == os.path.normcase(path)


def test_config_file_path():
    runner = Runner(os.path.join('foo', 'bar'), C.CONFIG_FILE)
    expected_path = os.path.join('foo', 'bar', C.CONFIG_FILE)
    assert runner.config_file_path == expected_path
