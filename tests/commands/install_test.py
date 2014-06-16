from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import os.path
import re
import pkg_resources
import subprocess
import stat
from plumbum import local

from pre_commit.commands.install import install
from pre_commit.runner import Runner
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo


def _get_commit_output(tmpdir_factory):
    # Don't want to write to home directory
    env = dict(os.environ, **{'PRE_COMMIT_HOME': tmpdir_factory.get()})
    return local['git'](
        'commit', '-m', 'Commit!', '--allow-empty',
        # git commit puts pre-commit to stderr
        stderr=subprocess.STDOUT,
        env=env,
    )


NORMAL_PRE_COMMIT_RUN = re.compile(
    r'^\[INFO\] Installing environment for .+.\n'
    r'\[INFO\] Once installed this environment will be reused.\n'
    r'\[INFO\] This may take a few minutes...\n'
    r'Bash hook'
    r'\.+'
    r'\(no files to check\) Skipped\n'
    r'\[master [a-f0-9]{7}\] Commit!\n$'
)


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


def test_install_pre_commit_and_run(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        assert install(Runner(path)) == 0

        output = _get_commit_output(tmpdir_factory)
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_install_idempotent(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        assert install(Runner(path)) == 0
        assert install(Runner(path)) == 0

        output = _get_commit_output(tmpdir_factory)
        assert NORMAL_PRE_COMMIT_RUN.match(output)
