from __future__ import absolute_import
from __future__ import unicode_literals

import os.path

from pre_commit.runner import Runner
from pre_commit.commands.install import install
from pre_commit.commands.uninstall import uninstall
from testing.fixtures import git_dir


def test_uninstall_does_not_blow_up_when_not_there(tmpdir_factory):
    path = git_dir(tmpdir_factory)
    runner = Runner(path)
    ret = uninstall(runner)
    assert ret == 0


def test_uninstall(tmpdir_factory):
    path = git_dir(tmpdir_factory)
    runner = Runner(path)
    assert not os.path.exists(runner.pre_commit_path)
    install(runner)
    assert os.path.exists(runner.pre_commit_path)
    uninstall(runner)
    assert not os.path.exists(runner.pre_commit_path)
