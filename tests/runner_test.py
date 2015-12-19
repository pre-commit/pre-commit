from __future__ import absolute_import
from __future__ import unicode_literals

import os
import os.path

import pre_commit.constants as C
from pre_commit.ordereddict import OrderedDict
from pre_commit.runner import Runner
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.fixtures import add_config_to_repo
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo


def test_init_has_no_side_effects(tmpdir):
    current_wd = os.getcwd()
    runner = Runner(tmpdir.strpath)
    assert runner.git_root == tmpdir.strpath
    assert os.getcwd() == current_wd


def test_create_sets_correct_directory(tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        runner = Runner.create()
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

        runner = Runner.create()
        assert os.path.normcase(runner.git_root) == os.path.normcase(path)
        assert os.path.normcase(os.getcwd()) == os.path.normcase(path)


def test_config_file_path():
    runner = Runner(os.path.join('foo', 'bar'))
    expected_path = os.path.join('foo', 'bar', C.CONFIG_FILE)
    assert runner.config_file_path == expected_path


def test_repositories(tempdir_factory, mock_out_store_directory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    runner = Runner(path)
    assert len(runner.repositories) == 1


def test_local_hooks(tempdir_factory, mock_out_store_directory):
    config = OrderedDict((
        ('repo', 'local'),
        ('hooks', (OrderedDict((
            ('id', 'arg-per-line'),
            ('name', 'Args per line hook'),
            ('entry', 'bin/hook.sh'),
            ('language', 'script'),
            ('files', ''),
            ('args', ['hello', 'world']),
        )), OrderedDict((
            ('id', 'do_not_commit'),
            ('name', 'Block if "DO NOT COMMIT" is found'),
            ('entry', 'DO NOT COMMIT'),
            ('language', 'pcre'),
            ('files', '^(.*)$'),
        ))))
    ))
    git_path = git_dir(tempdir_factory)
    add_config_to_repo(git_path, config)
    runner = Runner(git_path)
    assert len(runner.repositories) == 1
    assert len(runner.repositories[0].hooks) == 2


def test_pre_commit_path(in_tmpdir):
    path = os.path.join('foo', 'bar')
    cmd_output('git', 'init', path)
    runner = Runner(path)
    expected_path = os.path.join(path, '.git', 'hooks', 'pre-commit')
    assert runner.pre_commit_path == expected_path


def test_pre_push_path(in_tmpdir):
    path = os.path.join('foo', 'bar')
    cmd_output('git', 'init', path)
    runner = Runner(path)
    expected_path = os.path.join(path, '.git', 'hooks', 'pre-push')
    assert runner.pre_push_path == expected_path


def test_cmd_runner(mock_out_store_directory):
    runner = Runner(os.path.join('foo', 'bar'))
    ret = runner.cmd_runner
    assert ret.prefix_dir == os.path.join(mock_out_store_directory) + os.sep
