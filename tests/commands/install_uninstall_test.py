from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import os.path
import re
import subprocess
import stat
from plumbum import local

from pre_commit.commands.install_uninstall import IDENTIFYING_HASH
from pre_commit.commands.install_uninstall import PREVIOUS_IDENTIFYING_HASHES
from pre_commit.commands.install_uninstall import install
from pre_commit.commands.install_uninstall import is_our_pre_commit
from pre_commit.commands.install_uninstall import is_previous_pre_commit
from pre_commit.commands.install_uninstall import make_executable
from pre_commit.commands.install_uninstall import uninstall
from pre_commit.runner import Runner
from pre_commit.util import resource_filename
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo


def test_is_not_our_pre_commit():
    assert is_our_pre_commit('setup.py') is False


def test_is_our_pre_commit():
    assert is_our_pre_commit(resource_filename('pre-commit-hook'))


def test_is_not_previous_pre_commit():
    assert is_previous_pre_commit('setup.py') is False


def test_is_also_not_previous_pre_commit():
    assert not is_previous_pre_commit(resource_filename('pre-commit-hook'))


def test_is_previous_pre_commit(in_tmpdir):
    with io.open('foo', 'w') as foo_file:
        foo_file.write(PREVIOUS_IDENTIFYING_HASHES[0])

    assert is_previous_pre_commit('foo')


def test_install_pre_commit(tmpdir_factory):
    path = git_dir(tmpdir_factory)
    runner = Runner(path)
    ret = install(runner)
    assert ret == 0
    assert os.path.exists(runner.pre_commit_path)
    pre_commit_contents = io.open(runner.pre_commit_path).read()
    pre_commit_script = resource_filename('pre-commit-hook')
    expected_contents = io.open(pre_commit_script).read()
    assert pre_commit_contents == expected_contents
    stat_result = os.stat(runner.pre_commit_path)
    assert stat_result.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


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


def _get_commit_output(tmpdir_factory, touch_file='foo', home=None):
    local['touch'](touch_file)
    local['git']('add', touch_file)
    # Don't want to write to home directory
    home = home or tmpdir_factory.get()
    env = dict(os.environ, **{'PRE_COMMIT_HOME': home})
    return local['git'].run(
        ['commit', '-m', 'Commit!', '--allow-empty'],
        # git commit puts pre-commit to stderr
        stderr=subprocess.STDOUT,
        env=env,
        retcode=None,
    )[:2]


# osx does this different :(
FILES_CHANGED = (
    r'('
    r' 1 file changed, 0 insertions\(\+\), 0 deletions\(-\)\n'
    r'|'
    r' 0 files changed\n'
    r')'
)


NORMAL_PRE_COMMIT_RUN = re.compile(
    r'^\[INFO\] Installing environment for .+\.\n'
    r'\[INFO\] Once installed this environment will be reused\.\n'
    r'\[INFO\] This may take a few minutes\.\.\.\n'
    r'Bash hook\.+Passed\n'
    r'\[master [a-f0-9]{7}\] Commit!\n' +
    FILES_CHANGED +
    r' create mode 100644 foo\n$'
)


def test_install_pre_commit_and_run(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        assert install(Runner(path)) == 0

        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_install_idempotent(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        assert install(Runner(path)) == 0
        assert install(Runner(path)) == 0

        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_environment_not_sourced(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        assert install(Runner(path)) == 0

        ret, stdout, stderr = local['git'].run(
            ['commit', '--allow-empty', '-m', 'foo'],
            # XXX: 'HOME' makes this test pass on OSX
            env={'HOME': os.environ['HOME']},
            retcode=None,
        )
        assert ret == 1
        assert stdout == ''
        assert stderr == (
            '`pre-commit` not found.  '
            'Did you forget to activate your virtualenv?\n'
        )


FAILING_PRE_COMMIT_RUN = re.compile(
    r'^\[INFO\] Installing environment for .+\.\n'
    r'\[INFO\] Once installed this environment will be reused\.\n'
    r'\[INFO\] This may take a few minutes\.\.\.\n'
    r'Failing hook\.+Failed\n'
    r'hookid: failing_hook\n'
    r'\n'
    r'Fail\n'
    r'foo\n'
    r'\n$'
)


def test_failing_hooks_returns_nonzero(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'failing_hook_repo')
    with local.cwd(path):
        assert install(Runner(path)) == 0

        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 1
        assert FAILING_PRE_COMMIT_RUN.match(output)


EXISTING_COMMIT_RUN = re.compile(
    r'^legacy hook\n'
    r'\[master [a-f0-9]{7}\] Commit!\n' +
    FILES_CHANGED +
    r' create mode 100644 baz\n$'
)


def test_install_existing_hooks_no_overwrite(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        runner = Runner(path)

        # Write out an "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        # Make sure we installed the "old" hook correctly
        ret, output = _get_commit_output(tmpdir_factory, touch_file='baz')
        assert ret == 0
        assert EXISTING_COMMIT_RUN.match(output)

        # Now install pre-commit (no-overwrite)
        assert install(runner) == 0

        # We should run both the legacy and pre-commit hooks
        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 0
        assert output.startswith('legacy hook\n')
        assert NORMAL_PRE_COMMIT_RUN.match(output[len('legacy hook\n'):])


def test_install_existing_hook_no_overwrite_idempotent(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        runner = Runner(path)

        # Write out an "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        # Install twice
        assert install(runner) == 0
        assert install(runner) == 0

        # We should run both the legacy and pre-commit hooks
        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 0
        assert output.startswith('legacy hook\n')
        assert NORMAL_PRE_COMMIT_RUN.match(output[len('legacy hook\n'):])


FAIL_OLD_HOOK = re.compile(
    r'fail!\n'
    r'\[INFO\] Installing environment for .+\.\n'
    r'\[INFO\] Once installed this environment will be reused\.\n'
    r'\[INFO\] This may take a few minutes\.\.\.\n'
    r'Bash hook\.+Passed\n'
)


def test_failing_existing_hook_returns_1(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        runner = Runner(path)

        # Write out a failing "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "fail!"\nexit 1\n')
        make_executable(runner.pre_commit_path)

        assert install(runner) == 0

        # We should get a failure from the legacy hook
        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 1
        assert FAIL_OLD_HOOK.match(output)


def test_install_overwrite_no_existing_hooks(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        assert install(Runner(path), overwrite=True) == 0

        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_install_overwrite(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        runner = Runner(path)

        # Write out the "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        assert install(runner, overwrite=True) == 0

        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_uninstall_restores_legacy_hooks(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        runner = Runner(path)

        # Write out an "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        # Now install and uninstall pre-commit
        assert install(runner) == 0
        assert uninstall(runner) == 0

        # Make sure we installed the "old" hook correctly
        ret, output = _get_commit_output(tmpdir_factory, touch_file='baz')
        assert ret == 0
        assert EXISTING_COMMIT_RUN.match(output)


def test_replace_old_commit_script(tmpdir_factory):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        runner = Runner(path)

        # Install a script that looks like our old script
        pre_commit_contents = io.open(
            resource_filename('pre-commit-hook'),
        ).read()
        new_contents = pre_commit_contents.replace(
            IDENTIFYING_HASH, PREVIOUS_IDENTIFYING_HASHES[-1],
        )

        with io.open(runner.pre_commit_path, 'w') as pre_commit_file:
            pre_commit_file.write(new_contents)
        make_executable(runner.pre_commit_path)

        # Install normally
        assert install(runner) == 0

        ret, output = _get_commit_output(tmpdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_uninstall_doesnt_remove_not_our_hooks(tmpdir_factory):
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        runner = Runner(path)
        with io.open(runner.pre_commit_path, 'w') as pre_commit_file:
            pre_commit_file.write('#!/usr/bin/env bash\necho 1\n')
        make_executable(runner.pre_commit_path)

        assert uninstall(runner) == 0

        assert os.path.exists(runner.pre_commit_path)


PRE_INSTALLED = re.compile(
    r'Bash hook\.+Passed\n'
    r'\[master [a-f0-9]{7}\] Commit!\n' +
    FILES_CHANGED +
    r' create mode 100644 foo\n$'
)


def test_installs_hooks_with_hooks_True(
        tmpdir_factory,
        mock_out_store_directory,
):
    path = make_consuming_repo(tmpdir_factory, 'script_hooks_repo')
    with local.cwd(path):
        install(Runner(path), hooks=True)
        ret, output = _get_commit_output(
            tmpdir_factory, home=mock_out_store_directory,
        )

        assert ret == 0
        assert PRE_INSTALLED.match(output)
