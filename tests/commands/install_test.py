from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import os.path
import pkg_resources
import stat

from pre_commit.commands.install import install
from pre_commit.runner import Runner
from testing.fixtures import git_dir


def test_install_pre_commit(tmpdir_factory):
    path = git_dir(tmpdir_factory)
    runner = Runner(path)
    ret = install(runner)
    assert ret == 0
    assert os.path.exists(runner.pre_commit_path)
    pre_commit_contents = io.open(runner.pre_commit_path).read()
    pre_commit_sh = pkg_resources.resource_filename(
        'pre_commit', 'resources/pre-commit.sh',
    )
    expected_contents = io.open(pre_commit_sh).read()
    assert pre_commit_contents == expected_contents
    stat_result = os.stat(runner.pre_commit_path)
    assert stat_result.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
