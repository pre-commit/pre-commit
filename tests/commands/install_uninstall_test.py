from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import os.path
import re
import shutil
import subprocess
import sys

import mock

from pre_commit.commands.install_uninstall import IDENTIFYING_HASH
from pre_commit.commands.install_uninstall import install
from pre_commit.commands.install_uninstall import is_our_pre_commit
from pre_commit.commands.install_uninstall import is_previous_pre_commit
from pre_commit.commands.install_uninstall import make_executable
from pre_commit.commands.install_uninstall import PREVIOUS_IDENTIFYING_HASHES
from pre_commit.commands.install_uninstall import uninstall
from pre_commit.runner import Runner
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from pre_commit.util import resource_filename
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo
from testing.util import xfailif_no_symlink


def test_is_not_our_pre_commit():
    assert is_our_pre_commit('setup.py') is False


def test_is_our_pre_commit():
    assert is_our_pre_commit(resource_filename('hook-tmpl'))


def test_is_not_previous_pre_commit():
    assert is_previous_pre_commit('setup.py') is False


def test_is_also_not_previous_pre_commit():
    assert not is_previous_pre_commit(resource_filename('hook-tmpl'))


def test_is_previous_pre_commit(in_tmpdir):
    with io.open('foo', 'w') as foo_file:
        foo_file.write(PREVIOUS_IDENTIFYING_HASHES[0])

    assert is_previous_pre_commit('foo')


def test_install_pre_commit(tempdir_factory):
    path = git_dir(tempdir_factory)
    runner = Runner(path)
    ret = install(runner)
    assert ret == 0
    assert os.path.exists(runner.pre_commit_path)
    pre_commit_contents = io.open(runner.pre_commit_path).read()
    pre_commit_script = resource_filename('hook-tmpl')
    expected_contents = io.open(pre_commit_script).read().format(
        sys_executable=sys.executable,
        hook_type='pre-commit',
        pre_push=''
    )
    assert pre_commit_contents == expected_contents
    assert os.access(runner.pre_commit_path, os.X_OK)

    ret = install(runner, hook_type='pre-push')
    assert ret == 0
    assert os.path.exists(runner.pre_push_path)
    pre_push_contents = io.open(runner.pre_push_path).read()
    pre_push_tmpl = resource_filename('pre-push-tmpl')
    pre_push_template_contents = io.open(pre_push_tmpl).read()
    expected_contents = io.open(pre_commit_script).read().format(
        sys_executable=sys.executable,
        hook_type='pre-push',
        pre_push=pre_push_template_contents,
    )
    assert pre_push_contents == expected_contents


def test_install_hooks_directory_not_present(tempdir_factory):
    path = git_dir(tempdir_factory)
    # Simulate some git clients which don't make .git/hooks #234
    shutil.rmtree(os.path.join(path, '.git', 'hooks'))
    runner = Runner(path)
    install(runner)
    assert os.path.exists(runner.pre_commit_path)


@xfailif_no_symlink
def test_install_hooks_dead_symlink(
        tempdir_factory,
):  # pragma: no cover (non-windows)
    path = git_dir(tempdir_factory)
    os.symlink('/fake/baz', os.path.join(path, '.git', 'hooks', 'pre-commit'))
    runner = Runner(path)
    install(runner)
    assert os.path.exists(runner.pre_commit_path)


def test_uninstall_does_not_blow_up_when_not_there(tempdir_factory):
    path = git_dir(tempdir_factory)
    runner = Runner(path)
    ret = uninstall(runner)
    assert ret == 0


def test_uninstall(tempdir_factory):
    path = git_dir(tempdir_factory)
    runner = Runner(path)
    assert not os.path.exists(runner.pre_commit_path)
    install(runner)
    assert os.path.exists(runner.pre_commit_path)
    uninstall(runner)
    assert not os.path.exists(runner.pre_commit_path)


def _get_commit_output(
        tempdir_factory,
        touch_file='foo',
        home=None,
        env_base=os.environ,
):
    cmd_output('touch', touch_file)
    cmd_output('git', 'add', touch_file)
    # Don't want to write to home directory
    home = home or tempdir_factory.get()
    env = dict(env_base, PRE_COMMIT_HOME=home)
    return cmd_output(
        'git', 'commit', '-m', 'Commit!', '--allow-empty',
        # git commit puts pre-commit to stderr
        stderr=subprocess.STDOUT,
        env=env,
        retcode=None,
    )[:2]


# osx does this different :(
FILES_CHANGED = (
    r'('
    r' 1 file changed, 0 insertions\(\+\), 0 deletions\(-\)\r?\n'
    r'|'
    r' 0 files changed\r?\n'
    r')'
)


NORMAL_PRE_COMMIT_RUN = re.compile(
    r'^\[INFO\] Initializing environment for .+\.\r?\n'
    r'Bash hook\.+Passed\r?\n'
    r'\[master [a-f0-9]{7}\] Commit!\r?\n' +
    FILES_CHANGED +
    r' create mode 100644 foo\r?\n$'
)


def test_install_pre_commit_and_run(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert install(Runner(path)) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_install_idempotent(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert install(Runner(path)) == 0
        assert install(Runner(path)) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def _path_without_us():
    # Choose a path which *probably* doesn't include us
    return os.pathsep.join([
        x for x in os.environ['PATH'].split(os.pathsep)
        if x.lower() != os.path.dirname(sys.executable).lower()
    ])


def test_environment_not_sourced(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        # Patch the executable to simulate rming virtualenv
        with mock.patch.object(sys, 'executable', '/bin/false'):
            assert install(Runner(path)) == 0

        # Use a specific homedir to ignore --user installs
        homedir = tempdir_factory.get()
        # Need this so we can call git commit without sploding
        with io.open(os.path.join(homedir, '.gitconfig'), 'w') as gitconfig:
            gitconfig.write(
                '[user]\n'
                '    name = Travis CI\n'
                '    email = user@example.com\n'
            )
        ret, stdout, stderr = cmd_output(
            'git', 'commit', '--allow-empty', '-m', 'foo',
            env={'HOME': homedir, 'PATH': _path_without_us()},
            retcode=None,
        )
        assert ret == 1
        assert stdout == ''
        assert stderr == (
            '`pre-commit` not found.  '
            'Did you forget to activate your virtualenv?\n'
        )


FAILING_PRE_COMMIT_RUN = re.compile(
    r'^\[INFO\] Initializing environment for .+\.\r?\n'
    r'Failing hook\.+Failed\r?\n'
    r'hookid: failing_hook\r?\n'
    r'\r?\n'
    r'Fail\r?\n'
    r'foo\r?\n'
    r'\r?\n$'
)


def test_failing_hooks_returns_nonzero(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'failing_hook_repo')
    with cwd(path):
        assert install(Runner(path)) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 1
        assert FAILING_PRE_COMMIT_RUN.match(output)


EXISTING_COMMIT_RUN = re.compile(
    r'^legacy hook\r?\n'
    r'\[master [a-f0-9]{7}\] Commit!\r?\n' +
    FILES_CHANGED +
    r' create mode 100644 baz\r?\n$'
)


def test_install_existing_hooks_no_overwrite(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        runner = Runner(path)

        # Write out an "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        # Make sure we installed the "old" hook correctly
        ret, output = _get_commit_output(tempdir_factory, touch_file='baz')
        assert ret == 0
        assert EXISTING_COMMIT_RUN.match(output)

        # Now install pre-commit (no-overwrite)
        assert install(runner) == 0

        # We should run both the legacy and pre-commit hooks
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert output.startswith('legacy hook\n')
        assert NORMAL_PRE_COMMIT_RUN.match(output[len('legacy hook\n'):])


def test_install_existing_hook_no_overwrite_idempotent(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        runner = Runner(path)

        # Write out an "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        # Install twice
        assert install(runner) == 0
        assert install(runner) == 0

        # We should run both the legacy and pre-commit hooks
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert output.startswith('legacy hook\n')
        assert NORMAL_PRE_COMMIT_RUN.match(output[len('legacy hook\n'):])


FAIL_OLD_HOOK = re.compile(
    r'fail!\r?\n'
    r'\[INFO\] Initializing environment for .+\.\r?\n'
    r'Bash hook\.+Passed\r?\n'
)


def test_failing_existing_hook_returns_1(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        runner = Runner(path)

        # Write out a failing "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "fail!"\nexit 1\n')
        make_executable(runner.pre_commit_path)

        assert install(runner) == 0

        # We should get a failure from the legacy hook
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 1
        assert FAIL_OLD_HOOK.match(output)


def test_install_overwrite_no_existing_hooks(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert install(Runner(path), overwrite=True) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_install_overwrite(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        runner = Runner(path)

        # Write out the "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        assert install(runner, overwrite=True) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_uninstall_restores_legacy_hooks(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        runner = Runner(path)

        # Write out an "old" hook
        with io.open(runner.pre_commit_path, 'w') as hook_file:
            hook_file.write('#!/usr/bin/env bash\necho "legacy hook"\n')
        make_executable(runner.pre_commit_path)

        # Now install and uninstall pre-commit
        assert install(runner) == 0
        assert uninstall(runner) == 0

        # Make sure we installed the "old" hook correctly
        ret, output = _get_commit_output(tempdir_factory, touch_file='baz')
        assert ret == 0
        assert EXISTING_COMMIT_RUN.match(output)


def test_replace_old_commit_script(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        runner = Runner(path)

        # Install a script that looks like our old script
        pre_commit_contents = io.open(
            resource_filename('hook-tmpl'),
        ).read()
        new_contents = pre_commit_contents.replace(
            IDENTIFYING_HASH, PREVIOUS_IDENTIFYING_HASHES[-1],
        )

        with io.open(runner.pre_commit_path, 'w') as pre_commit_file:
            pre_commit_file.write(new_contents)
        make_executable(runner.pre_commit_path)

        # Install normally
        assert install(runner) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def test_uninstall_doesnt_remove_not_our_hooks(tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        runner = Runner(path)
        with io.open(runner.pre_commit_path, 'w') as pre_commit_file:
            pre_commit_file.write('#!/usr/bin/env bash\necho 1\n')
        make_executable(runner.pre_commit_path)

        assert uninstall(runner) == 0

        assert os.path.exists(runner.pre_commit_path)


PRE_INSTALLED = re.compile(
    r'Bash hook\.+Passed\r?\n'
    r'\[master [a-f0-9]{7}\] Commit!\r?\n' +
    FILES_CHANGED +
    r' create mode 100644 foo\r?\n$'
)


def test_installs_hooks_with_hooks_True(
        tempdir_factory,
        mock_out_store_directory,
):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        install(Runner(path), hooks=True)
        ret, output = _get_commit_output(
            tempdir_factory, home=mock_out_store_directory,
        )

        assert ret == 0
        assert PRE_INSTALLED.match(output)


def test_installed_from_venv(tempdir_factory):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        install(Runner(path))
        # No environment so pre-commit is not on the path when running!
        # Should still pick up the python from when we installed
        ret, output = _get_commit_output(
            tempdir_factory,
            env_base={
                'HOME': os.path.expanduser('~'),
                'PATH': _path_without_us(),
                'TERM': os.environ.get('TERM', ''),
                # Windows needs this to import `random`
                'SYSTEMROOT': os.environ.get('SYSTEMROOT', ''),
            },
        )
        assert ret == 0
        assert NORMAL_PRE_COMMIT_RUN.match(output)


def _get_push_output(tempdir_factory):
    # Don't want to write to home directory
    home = tempdir_factory.get()
    env = dict(os.environ, PRE_COMMIT_HOME=home)
    return cmd_output(
        'git', 'push', 'origin', 'HEAD:new_branch',
        # git commit puts pre-commit to stderr
        stderr=subprocess.STDOUT,
        env=env,
        retcode=None,
    )[:2]


def test_pre_push_integration_failing(tempdir_factory):
    upstream = make_consuming_repo(tempdir_factory, 'failing_hook_repo')
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        install(Runner(path), hook_type='pre-push')
        # commit succeeds because pre-commit is only installed for pre-push
        assert _get_commit_output(tempdir_factory)[0] == 0

        retc, output = _get_push_output(tempdir_factory)
        assert retc == 1
        assert 'Failing hook' in output
        assert 'Failed' in output
        assert 'hookid: failing_hook' in output


def test_pre_push_integration_accepted(tempdir_factory):
    upstream = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        install(Runner(path), hook_type='pre-push')
        assert _get_commit_output(tempdir_factory)[0] == 0

        retc, output = _get_push_output(tempdir_factory)
        assert retc == 0
        assert 'Bash hook' in output
        assert 'Passed' in output


def test_pre_push_integration_empty_push(tempdir_factory):
    upstream = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        install(Runner(path), hook_type='pre-push')
        _get_push_output(tempdir_factory)
        retc, output = _get_push_output(tempdir_factory)
        assert output == 'Everything up-to-date\n'
        assert retc == 0
