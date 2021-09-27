import os.path
import re
import sys
from unittest import mock

import re_assert

import pre_commit.constants as C
from pre_commit import git
from pre_commit.commands import install_uninstall
from pre_commit.commands.install_uninstall import CURRENT_HASH
from pre_commit.commands.install_uninstall import install
from pre_commit.commands.install_uninstall import install_hooks
from pre_commit.commands.install_uninstall import is_our_script
from pre_commit.commands.install_uninstall import PRIOR_HASHES
from pre_commit.commands.install_uninstall import shebang
from pre_commit.commands.install_uninstall import uninstall
from pre_commit.parse_shebang import find_executable
from pre_commit.util import cmd_output
from pre_commit.util import make_executable
from pre_commit.util import resource_text
from testing.fixtures import add_config_to_repo
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo
from testing.fixtures import remove_config_from_repo
from testing.fixtures import write_config
from testing.util import cmd_output_mocked_pre_commit_home
from testing.util import cwd
from testing.util import git_commit


def test_is_not_script():
    assert is_our_script('setup.py') is False


def test_is_script():
    assert is_our_script('pre_commit/resources/hook-tmpl')


def test_is_previous_pre_commit(tmpdir):
    f = tmpdir.join('foo')
    f.write(f'{PRIOR_HASHES[0].decode()}\n')
    assert is_our_script(f.strpath)


def patch_platform(platform):
    return mock.patch.object(sys, 'platform', platform)


def patch_lookup_path(path):
    return mock.patch.object(install_uninstall, 'POSIX_SEARCH_PATH', path)


def patch_sys_exe(exe):
    return mock.patch.object(install_uninstall, 'SYS_EXE', exe)


def test_shebang_windows():
    with patch_platform('win32'), patch_sys_exe('python'):
        assert shebang() == '#!/usr/bin/env python'


def test_shebang_windows_drop_ext():
    with patch_platform('win32'), patch_sys_exe('python.exe'):
        assert shebang() == '#!/usr/bin/env python'


def test_shebang_posix_not_on_path():
    with patch_platform('posix'), patch_lookup_path(()):
        with patch_sys_exe('python3.6'):
            assert shebang() == '#!/usr/bin/env python3.6'


def test_shebang_posix_on_path(tmpdir):
    exe = tmpdir.join(f'python{sys.version_info[0]}').ensure()
    make_executable(exe)

    with patch_platform('posix'), patch_lookup_path((tmpdir.strpath,)):
        with patch_sys_exe('python'):
            assert shebang() == f'#!/usr/bin/env python{sys.version_info[0]}'


def test_install_pre_commit(in_git_dir, store):
    assert not install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
    assert os.access(in_git_dir.join('.git/hooks/pre-commit').strpath, os.X_OK)

    assert not install(C.CONFIG_FILE, store, hook_types=['pre-push'])
    assert os.access(in_git_dir.join('.git/hooks/pre-push').strpath, os.X_OK)


def test_install_hooks_directory_not_present(in_git_dir, store):
    # Simulate some git clients which don't make .git/hooks #234
    if in_git_dir.join('.git/hooks').exists():  # pragma: no cover (odd git)
        in_git_dir.join('.git/hooks').remove()
    install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
    assert in_git_dir.join('.git/hooks/pre-commit').exists()


def test_install_multiple_hooks_at_once(in_git_dir, store):
    install(C.CONFIG_FILE, store, hook_types=['pre-commit', 'pre-push'])
    assert in_git_dir.join('.git/hooks/pre-commit').exists()
    assert in_git_dir.join('.git/hooks/pre-push').exists()
    uninstall(hook_types=['pre-commit', 'pre-push'])
    assert not in_git_dir.join('.git/hooks/pre-commit').exists()
    assert not in_git_dir.join('.git/hooks/pre-push').exists()


def test_install_refuses_core_hookspath(in_git_dir, store):
    cmd_output('git', 'config', '--local', 'core.hooksPath', 'hooks')
    assert install(C.CONFIG_FILE, store, hook_types=['pre-commit'])


def test_install_hooks_dead_symlink(in_git_dir, store):
    hook = in_git_dir.join('.git/hooks').ensure_dir().join('pre-commit')
    os.symlink('/fake/baz', hook.strpath)
    install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
    assert hook.exists()


def test_uninstall_does_not_blow_up_when_not_there(in_git_dir):
    assert uninstall(hook_types=['pre-commit']) == 0


def test_uninstall(in_git_dir, store):
    assert not in_git_dir.join('.git/hooks/pre-commit').exists()
    install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
    assert in_git_dir.join('.git/hooks/pre-commit').exists()
    uninstall(hook_types=['pre-commit'])
    assert not in_git_dir.join('.git/hooks/pre-commit').exists()


def _get_commit_output(tempdir_factory, touch_file='foo', **kwargs):
    open(touch_file, 'a').close()
    cmd_output('git', 'add', touch_file)
    return git_commit(
        fn=cmd_output_mocked_pre_commit_home,
        retcode=None,
        tempdir_factory=tempdir_factory,
        **kwargs,
    )


# osx does this different :(
FILES_CHANGED = (
    r'('
    r' 1 file changed, 0 insertions\(\+\), 0 deletions\(-\)\n'
    r'|'
    r' 0 files changed\n'
    r')'
)


NORMAL_PRE_COMMIT_RUN = re_assert.Matches(
    fr'^\[INFO\] Initializing environment for .+\.\n'
    fr'Bash hook\.+Passed\n'
    fr'\[master [a-f0-9]{{7}}\] commit!\n'
    fr'{FILES_CHANGED}'
    fr' create mode 100644 foo\n$',
)


def test_install_pre_commit_and_run(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def test_install_pre_commit_and_run_custom_path(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        cmd_output('git', 'mv', C.CONFIG_FILE, 'custom.yaml')
        git_commit(cwd=path)
        assert install('custom.yaml', store, hook_types=['pre-commit']) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def test_install_in_submodule_and_run(tempdir_factory, store):
    src_path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    parent_path = git_dir(tempdir_factory)
    cmd_output('git', 'submodule', 'add', src_path, 'sub', cwd=parent_path)
    git_commit(cwd=parent_path)

    sub_pth = os.path.join(parent_path, 'sub')
    with cwd(sub_pth):
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def test_install_in_worktree_and_run(tempdir_factory, store):
    src_path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    path = tempdir_factory.get()
    cmd_output('git', '-C', src_path, 'branch', '-m', 'notmaster')
    cmd_output('git', '-C', src_path, 'worktree', 'add', path, '-b', 'master')

    with cwd(path):
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def test_commit_am(tempdir_factory, store):
    """Regression test for #322."""
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        # Make an unstaged change
        open('unstaged', 'w').close()
        cmd_output('git', 'add', '.')
        git_commit(cwd=path)
        with open('unstaged', 'w') as foo_file:
            foo_file.write('Oh hai')

        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0


def test_unicode_merge_commit_message(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0
        cmd_output('git', 'checkout', 'master', '-b', 'foo')
        git_commit('-n', cwd=path)
        cmd_output('git', 'checkout', 'master')
        cmd_output('git', 'merge', 'foo', '--no-ff', '--no-commit', '-m', '☃')
        # Used to crash
        git_commit(
            '--no-edit',
            msg=None,
            fn=cmd_output_mocked_pre_commit_home,
            tempdir_factory=tempdir_factory,
        )


def test_install_idempotent(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def _path_without_us():
    # Choose a path which *probably* doesn't include us
    env = dict(os.environ)
    exe = find_executable('pre-commit', _environ=env)
    while exe:
        parts = env['PATH'].split(os.pathsep)
        after = [
            x for x in parts
            if x.lower().rstrip(os.sep) != os.path.dirname(exe).lower()
        ]
        if parts == after:
            raise AssertionError(exe, parts)
        env['PATH'] = os.pathsep.join(after)
        exe = find_executable('pre-commit', _environ=env)
    return env['PATH']


def test_environment_not_sourced(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert not install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
        # simulate deleting the virtualenv by rewriting the exe
        hook = os.path.join(path, '.git/hooks/pre-commit')
        with open(hook) as f:
            src = f.read()
        src = re.sub('\nINSTALL_PYTHON=.*\n', '\nINSTALL_PYTHON="/dne"\n', src)
        with open(hook, 'w') as f:
            f.write(src)

        # Use a specific homedir to ignore --user installs
        homedir = tempdir_factory.get()
        ret, out = git_commit(
            env={
                'HOME': homedir,
                'PATH': _path_without_us(),
                # Git needs this to make a commit
                'GIT_AUTHOR_NAME': os.environ['GIT_AUTHOR_NAME'],
                'GIT_COMMITTER_NAME': os.environ['GIT_COMMITTER_NAME'],
                'GIT_AUTHOR_EMAIL': os.environ['GIT_AUTHOR_EMAIL'],
                'GIT_COMMITTER_EMAIL': os.environ['GIT_COMMITTER_EMAIL'],
            },
            retcode=None,
        )
        assert ret == 1
        assert out == (
            '`pre-commit` not found.  '
            'Did you forget to activate your virtualenv?\n'
        )


FAILING_PRE_COMMIT_RUN = re_assert.Matches(
    r'^\[INFO\] Initializing environment for .+\.\n'
    r'Failing hook\.+Failed\n'
    r'- hook id: failing_hook\n'
    r'- exit code: 1\n'
    r'\n'
    r'Fail\n'
    r'foo\n'
    r'\n$',
)


def test_failing_hooks_returns_nonzero(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'failing_hook_repo')
    with cwd(path):
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 1
        FAILING_PRE_COMMIT_RUN.assert_matches(output)


EXISTING_COMMIT_RUN = re_assert.Matches(
    fr'^legacy hook\n'
    fr'\[master [a-f0-9]{{7}}\] commit!\n'
    fr'{FILES_CHANGED}'
    fr' create mode 100644 baz\n$',
)


def _write_legacy_hook(path):
    os.makedirs(os.path.join(path, '.git/hooks'), exist_ok=True)
    with open(os.path.join(path, '.git/hooks/pre-commit'), 'w') as f:
        f.write(f'{shebang()}\nprint("legacy hook")\n')
    make_executable(f.name)


def test_install_existing_hooks_no_overwrite(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        _write_legacy_hook(path)

        # Make sure we installed the "old" hook correctly
        ret, output = _get_commit_output(tempdir_factory, touch_file='baz')
        assert ret == 0
        EXISTING_COMMIT_RUN.assert_matches(output)

        # Now install pre-commit (no-overwrite)
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        # We should run both the legacy and pre-commit hooks
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert output.startswith('legacy hook\n')
        NORMAL_PRE_COMMIT_RUN.assert_matches(output[len('legacy hook\n'):])


def test_legacy_overwriting_legacy_hook(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        _write_legacy_hook(path)
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0
        _write_legacy_hook(path)
        # this previously crashed on windows.  See #1010
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0


def test_install_existing_hook_no_overwrite_idempotent(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        _write_legacy_hook(path)

        # Install twice
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        # We should run both the legacy and pre-commit hooks
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        assert output.startswith('legacy hook\n')
        NORMAL_PRE_COMMIT_RUN.assert_matches(output[len('legacy hook\n'):])


def test_install_with_existing_non_utf8_script(tmpdir, store):
    cmd_output('git', 'init', str(tmpdir))
    tmpdir.join('.git/hooks').ensure_dir()
    tmpdir.join('.git/hooks/pre-commit').write_binary(
        b'#!/usr/bin/env bash\n'
        b'# garbage: \xa0\xef\x12\xf2\n'
        b'echo legacy hook\n',
    )

    with tmpdir.as_cwd():
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0


FAIL_OLD_HOOK = re_assert.Matches(
    r'fail!\n'
    r'\[INFO\] Initializing environment for .+\.\n'
    r'Bash hook\.+Passed\n',
)


def test_failing_existing_hook_returns_1(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        # Write out a failing "old" hook
        os.makedirs(os.path.join(path, '.git/hooks'), exist_ok=True)
        with open(os.path.join(path, '.git/hooks/pre-commit'), 'w') as f:
            f.write('#!/usr/bin/env bash\necho "fail!"\nexit 1\n')
        make_executable(f.name)

        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        # We should get a failure from the legacy hook
        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 1
        FAIL_OLD_HOOK.assert_matches(output)


def test_install_overwrite_no_existing_hooks(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        assert not install(
            C.CONFIG_FILE, store, hook_types=['pre-commit'], overwrite=True,
        )

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def test_install_overwrite(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        _write_legacy_hook(path)
        assert not install(
            C.CONFIG_FILE, store, hook_types=['pre-commit'], overwrite=True,
        )

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def test_uninstall_restores_legacy_hooks(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        _write_legacy_hook(path)

        # Now install and uninstall pre-commit
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0
        assert uninstall(hook_types=['pre-commit']) == 0

        # Make sure we installed the "old" hook correctly
        ret, output = _get_commit_output(tempdir_factory, touch_file='baz')
        assert ret == 0
        EXISTING_COMMIT_RUN.assert_matches(output)


def test_replace_old_commit_script(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        # Install a script that looks like our old script
        pre_commit_contents = resource_text('hook-tmpl')
        new_contents = pre_commit_contents.replace(
            CURRENT_HASH.decode(), PRIOR_HASHES[-1].decode(),
        )

        os.makedirs(os.path.join(path, '.git/hooks'), exist_ok=True)
        with open(os.path.join(path, '.git/hooks/pre-commit'), 'w') as f:
            f.write(new_contents)
        make_executable(f.name)

        # Install normally
        assert install(C.CONFIG_FILE, store, hook_types=['pre-commit']) == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def test_uninstall_doesnt_remove_not_our_hooks(in_git_dir):
    pre_commit = in_git_dir.join('.git/hooks').ensure_dir().join('pre-commit')
    pre_commit.write('#!/usr/bin/env bash\necho 1\n')
    make_executable(pre_commit.strpath)

    assert uninstall(hook_types=['pre-commit']) == 0

    assert pre_commit.exists()


PRE_INSTALLED = re_assert.Matches(
    fr'Bash hook\.+Passed\n'
    fr'\[master [a-f0-9]{{7}}\] commit!\n'
    fr'{FILES_CHANGED}'
    fr' create mode 100644 foo\n$',
)


def test_installs_hooks_with_hooks_True(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        install(C.CONFIG_FILE, store, hook_types=['pre-commit'], hooks=True)
        ret, output = _get_commit_output(
            tempdir_factory, pre_commit_home=store.directory,
        )

        assert ret == 0
        PRE_INSTALLED.assert_matches(output)


def test_install_hooks_command(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
        install_hooks(C.CONFIG_FILE, store)
        ret, output = _get_commit_output(
            tempdir_factory, pre_commit_home=store.directory,
        )

        assert ret == 0
        PRE_INSTALLED.assert_matches(output)


def test_installed_from_venv(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
        # No environment so pre-commit is not on the path when running!
        # Should still pick up the python from when we installed
        ret, output = _get_commit_output(
            tempdir_factory,
            env={
                'HOME': os.path.expanduser('~'),
                'PATH': _path_without_us(),
                'TERM': os.environ.get('TERM', ''),
                # Windows needs this to import `random`
                'SYSTEMROOT': os.environ.get('SYSTEMROOT', ''),
                # Windows needs this to resolve executables
                'PATHEXT': os.environ.get('PATHEXT', ''),
                # Git needs this to make a commit
                'GIT_AUTHOR_NAME': os.environ['GIT_AUTHOR_NAME'],
                'GIT_COMMITTER_NAME': os.environ['GIT_COMMITTER_NAME'],
                'GIT_AUTHOR_EMAIL': os.environ['GIT_AUTHOR_EMAIL'],
                'GIT_COMMITTER_EMAIL': os.environ['GIT_COMMITTER_EMAIL'],
            },
        )
        assert ret == 0
        NORMAL_PRE_COMMIT_RUN.assert_matches(output)


def _get_push_output(tempdir_factory, remote='origin', opts=()):
    return cmd_output_mocked_pre_commit_home(
        'git', 'push', remote, 'HEAD:new_branch', *opts,
        tempdir_factory=tempdir_factory,
        retcode=None,
    )[:2]


def test_pre_push_integration_failing(tempdir_factory, store):
    upstream = make_consuming_repo(tempdir_factory, 'failing_hook_repo')
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        install(C.CONFIG_FILE, store, hook_types=['pre-push'])
        # commit succeeds because pre-commit is only installed for pre-push
        assert _get_commit_output(tempdir_factory)[0] == 0
        assert _get_commit_output(tempdir_factory, touch_file='zzz')[0] == 0

        retc, output = _get_push_output(tempdir_factory)
        assert retc == 1
        assert 'Failing hook' in output
        assert 'Failed' in output
        assert 'foo zzz' in output  # both filenames should be printed
        assert 'hook id: failing_hook' in output


def test_pre_push_integration_accepted(tempdir_factory, store):
    upstream = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        install(C.CONFIG_FILE, store, hook_types=['pre-push'])
        assert _get_commit_output(tempdir_factory)[0] == 0

        retc, output = _get_push_output(tempdir_factory)
        assert retc == 0
        assert 'Bash hook' in output
        assert 'Passed' in output


def test_pre_push_force_push_without_fetch(tempdir_factory, store):
    upstream = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    path1 = tempdir_factory.get()
    path2 = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path1)
    cmd_output('git', 'clone', upstream, path2)
    with cwd(path1):
        assert _get_commit_output(tempdir_factory)[0] == 0
        assert _get_push_output(tempdir_factory)[0] == 0

    with cwd(path2):
        install(C.CONFIG_FILE, store, hook_types=['pre-push'])
        assert _get_commit_output(tempdir_factory, msg='force!')[0] == 0

        retc, output = _get_push_output(tempdir_factory, opts=('--force',))
        assert retc == 0
        assert 'Bash hook' in output
        assert 'Passed' in output


def test_pre_push_new_upstream(tempdir_factory, store):
    upstream = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    upstream2 = git_dir(tempdir_factory)
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        install(C.CONFIG_FILE, store, hook_types=['pre-push'])
        assert _get_commit_output(tempdir_factory)[0] == 0

        cmd_output('git', 'remote', 'rename', 'origin', 'upstream')
        cmd_output('git', 'remote', 'add', 'origin', upstream2)
        retc, output = _get_push_output(tempdir_factory)
        assert retc == 0
        assert 'Bash hook' in output
        assert 'Passed' in output


def test_pre_push_environment_variables(tempdir_factory, store):
    config = {
        'repo': 'local',
        'hooks': [
            {
                'id': 'print-remote-info',
                'name': 'print remote info',
                'entry': 'bash -c "echo remote: $PRE_COMMIT_REMOTE_NAME"',
                'language': 'system',
                'verbose': True,
            },
        ],
    }

    upstream = git_dir(tempdir_factory)
    clone = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, clone)
    add_config_to_repo(clone, config)
    with cwd(clone):
        install(C.CONFIG_FILE, store, hook_types=['pre-push'])

        cmd_output('git', 'remote', 'rename', 'origin', 'origin2')
        retc, output = _get_push_output(tempdir_factory, remote='origin2')
        assert retc == 0
        assert '\nremote: origin2\n' in output


def test_pre_push_integration_empty_push(tempdir_factory, store):
    upstream = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        install(C.CONFIG_FILE, store, hook_types=['pre-push'])
        _get_push_output(tempdir_factory)
        retc, output = _get_push_output(tempdir_factory)
        assert output == 'Everything up-to-date\n'
        assert retc == 0


def test_pre_push_legacy(tempdir_factory, store):
    upstream = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    path = tempdir_factory.get()
    cmd_output('git', 'clone', upstream, path)
    with cwd(path):
        os.makedirs(os.path.join(path, '.git/hooks'), exist_ok=True)
        with open(os.path.join(path, '.git/hooks/pre-push'), 'w') as f:
            f.write(
                '#!/usr/bin/env bash\n'
                'set -eu\n'
                'read lr ls rr rs\n'
                'test -n "$lr" -a -n "$ls" -a -n "$rr" -a -n "$rs"\n'
                'echo legacy\n',
            )
        make_executable(f.name)

        install(C.CONFIG_FILE, store, hook_types=['pre-push'])
        assert _get_commit_output(tempdir_factory)[0] == 0

        retc, output = _get_push_output(tempdir_factory)
        assert retc == 0
        first_line, _, third_line = output.splitlines()[:3]
        assert first_line == 'legacy'
        assert third_line.startswith('Bash hook')
        assert third_line.endswith('Passed')


def test_commit_msg_integration_failing(
        commit_msg_repo, tempdir_factory, store,
):
    install(C.CONFIG_FILE, store, hook_types=['commit-msg'])
    retc, out = _get_commit_output(tempdir_factory)
    assert retc == 1
    assert out == '''\
Must have "Signed off by:"...............................................Failed
- hook id: must-have-signoff
- exit code: 1
'''


def test_commit_msg_integration_passing(
        commit_msg_repo, tempdir_factory, store,
):
    install(C.CONFIG_FILE, store, hook_types=['commit-msg'])
    msg = 'Hi\nSigned off by: me, lol'
    retc, out = _get_commit_output(tempdir_factory, msg=msg)
    assert retc == 0
    first_line = out.splitlines()[0]
    assert first_line.startswith('Must have "Signed off by:"...')
    assert first_line.endswith('...Passed')


def test_commit_msg_legacy(commit_msg_repo, tempdir_factory, store):
    hook_path = os.path.join(commit_msg_repo, '.git/hooks/commit-msg')
    os.makedirs(os.path.dirname(hook_path), exist_ok=True)
    with open(hook_path, 'w') as hook_file:
        hook_file.write(
            '#!/usr/bin/env bash\n'
            'set -eu\n'
            'test -e "$1"\n'
            'echo legacy\n',
        )
    make_executable(hook_path)

    install(C.CONFIG_FILE, store, hook_types=['commit-msg'])

    msg = 'Hi\nSigned off by: asottile'
    retc, out = _get_commit_output(tempdir_factory, msg=msg)
    assert retc == 0
    first_line, second_line = out.splitlines()[:2]
    assert first_line == 'legacy'
    assert second_line.startswith('Must have "Signed off by:"...')


def test_post_commit_integration(tempdir_factory, store):
    path = git_dir(tempdir_factory)
    config = [
        {
            'repo': 'local',
            'hooks': [{
                'id': 'post-commit',
                'name': 'Post commit',
                'entry': 'touch post-commit.tmp',
                'language': 'system',
                'always_run': True,
                'verbose': True,
                'stages': ['post-commit'],
            }],
        },
    ]
    write_config(path, config)
    with cwd(path):
        _get_commit_output(tempdir_factory)
        assert not os.path.exists('post-commit.tmp')

        install(C.CONFIG_FILE, store, hook_types=['post-commit'])
        _get_commit_output(tempdir_factory)
        assert os.path.exists('post-commit.tmp')


def test_post_merge_integration(tempdir_factory, store):
    path = git_dir(tempdir_factory)
    config = [
        {
            'repo': 'local',
            'hooks': [{
                'id': 'post-merge',
                'name': 'Post merge',
                'entry': 'touch post-merge.tmp',
                'language': 'system',
                'always_run': True,
                'verbose': True,
                'stages': ['post-merge'],
            }],
        },
    ]
    write_config(path, config)
    with cwd(path):
        #  create a simple diamond of commits for a non-trivial merge
        open('init', 'a').close()
        cmd_output('git', 'add', '.')
        git_commit()

        open('master', 'a').close()
        cmd_output('git', 'add', '.')
        git_commit()

        cmd_output('git', 'checkout', '-b', 'branch', 'HEAD^')
        open('branch', 'a').close()
        cmd_output('git', 'add', '.')
        git_commit()

        cmd_output('git', 'checkout', 'master')
        install(C.CONFIG_FILE, store, hook_types=['post-merge'])
        retc, stdout, stderr = cmd_output_mocked_pre_commit_home(
            'git', 'merge', 'branch',
            tempdir_factory=tempdir_factory,
        )
        assert retc == 0
        assert os.path.exists('post-merge.tmp')


def test_post_rewrite_integration(tempdir_factory, store):
    path = git_dir(tempdir_factory)
    config = [
        {
            'repo': 'local',
            'hooks': [{
                'id': 'post-rewrite',
                'name': 'Post rewrite',
                'entry': 'touch post-rewrite.tmp',
                'language': 'system',
                'always_run': True,
                'verbose': True,
                'stages': ['post-rewrite'],
            }],
        },
    ]
    write_config(path, config)
    with cwd(path):
        open('init', 'a').close()
        cmd_output('git', 'add', '.')
        install(C.CONFIG_FILE, store, hook_types=['post-rewrite'])
        git_commit()

        assert not os.path.exists('post-rewrite.tmp')

        git_commit('--amend', '-m', 'ammended message')
        assert os.path.exists('post-rewrite.tmp')


def test_post_checkout_integration(tempdir_factory, store):
    path = git_dir(tempdir_factory)
    config = [
        {
            'repo': 'local',
            'hooks': [{
                'id': 'post-checkout',
                'name': 'Post checkout',
                'entry': 'bash -c "echo ${PRE_COMMIT_TO_REF}"',
                'language': 'system',
                'always_run': True,
                'verbose': True,
                'stages': ['post-checkout'],
            }],
        },
        {'repo': 'meta', 'hooks': [{'id': 'identity'}]},
    ]
    write_config(path, config)
    with cwd(path):
        cmd_output('git', 'add', '.')
        git_commit()

        # add a file only on `feature`, it should not be passed to hooks
        cmd_output('git', 'checkout', '-b', 'feature')
        open('some_file', 'a').close()
        cmd_output('git', 'add', '.')
        git_commit()
        cmd_output('git', 'checkout', 'master')

        install(C.CONFIG_FILE, store, hook_types=['post-checkout'])
        retc, _, stderr = cmd_output('git', 'checkout', 'feature')
        assert stderr is not None
        assert retc == 0
        assert git.head_rev(path) in stderr
        assert 'some_file' not in stderr


def test_skips_post_checkout_unstaged_changes(tempdir_factory, store):
    path = git_dir(tempdir_factory)
    config = {
        'repo': 'local',
        'hooks': [{
            'id': 'fail',
            'name': 'fail',
            'entry': 'fail',
            'language': 'fail',
            'always_run': True,
            'stages': ['post-checkout'],
        }],
    }
    write_config(path, config)
    with cwd(path):
        cmd_output('git', 'add', '.')
        _get_commit_output(tempdir_factory)

        install(C.CONFIG_FILE, store, hook_types=['pre-commit'])
        install(C.CONFIG_FILE, store, hook_types=['post-checkout'])

        # make an unstaged change so staged_files_only fires
        open('file', 'a').close()
        cmd_output('git', 'add', 'file')
        with open('file', 'w') as f:
            f.write('unstaged changes')

        retc, out = _get_commit_output(tempdir_factory, all_files=False)
        assert retc == 0


def test_prepare_commit_msg_integration_failing(
        failing_prepare_commit_msg_repo, tempdir_factory, store,
):
    install(C.CONFIG_FILE, store, hook_types=['prepare-commit-msg'])
    retc, out = _get_commit_output(tempdir_factory)
    assert retc == 1
    assert out == '''\
Add "Signed off by:".....................................................Failed
- hook id: add-signoff
- exit code: 1
'''


def test_prepare_commit_msg_integration_passing(
        prepare_commit_msg_repo, tempdir_factory, store,
):
    install(C.CONFIG_FILE, store, hook_types=['prepare-commit-msg'])
    retc, out = _get_commit_output(tempdir_factory, msg='Hi')
    assert retc == 0
    first_line = out.splitlines()[0]
    assert first_line.startswith('Add "Signed off by:"...')
    assert first_line.endswith('...Passed')
    commit_msg_path = os.path.join(
        prepare_commit_msg_repo, '.git/COMMIT_EDITMSG',
    )
    with open(commit_msg_path) as f:
        assert 'Signed off by: ' in f.read()


def test_prepare_commit_msg_legacy(
    prepare_commit_msg_repo, tempdir_factory, store,
):
    hook_path = os.path.join(
        prepare_commit_msg_repo, '.git/hooks/prepare-commit-msg',
    )
    os.makedirs(os.path.dirname(hook_path), exist_ok=True)
    with open(hook_path, 'w') as hook_file:
        hook_file.write(
            '#!/usr/bin/env bash\n'
            'set -eu\n'
            'test -e "$1"\n'
            'echo legacy\n',
        )
    make_executable(hook_path)

    install(C.CONFIG_FILE, store, hook_types=['prepare-commit-msg'])

    retc, out = _get_commit_output(tempdir_factory, msg='Hi')
    assert retc == 0
    first_line, second_line = out.splitlines()[:2]
    assert first_line == 'legacy'
    assert second_line.startswith('Add "Signed off by:"...')
    commit_msg_path = os.path.join(
        prepare_commit_msg_repo, '.git/COMMIT_EDITMSG',
    )
    with open(commit_msg_path) as f:
        assert 'Signed off by: ' in f.read()


def test_pre_merge_commit_integration(tempdir_factory, store):
    output_pattern = re_assert.Matches(
        r'^\[INFO\] Initializing environment for .+\n'
        r'Bash hook\.+Passed\n'
        r"Merge made by the '(ort|recursive)' strategy.\n"
        r' foo \| 0\n'
        r' 1 file changed, 0 insertions\(\+\), 0 deletions\(-\)\n'
        r' create mode 100644 foo\n$',
    )

    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        ret = install(C.CONFIG_FILE, store, hook_types=['pre-merge-commit'])
        assert ret == 0

        cmd_output('git', 'checkout', 'master', '-b', 'feature')
        _get_commit_output(tempdir_factory)
        cmd_output('git', 'checkout', 'master')
        ret, output, _ = cmd_output_mocked_pre_commit_home(
            'git', 'merge', '--no-ff', '--no-edit', 'feature',
            tempdir_factory=tempdir_factory,
        )
        assert ret == 0
        output_pattern.assert_matches(output)


def test_install_disallow_missing_config(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        remove_config_from_repo(path)
        ret = install(
            C.CONFIG_FILE, store, hook_types=['pre-commit'],
            overwrite=True, skip_on_missing_config=False,
        )
        assert ret == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 1


def test_install_allow_missing_config(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        remove_config_from_repo(path)
        ret = install(
            C.CONFIG_FILE, store, hook_types=['pre-commit'],
            overwrite=True, skip_on_missing_config=True,
        )
        assert ret == 0

        ret, output = _get_commit_output(tempdir_factory)
        assert ret == 0
        expected = (
            '`.pre-commit-config.yaml` config file not found. '
            'Skipping `pre-commit`.'
        )
        assert expected in output


def test_install_temporarily_allow_mising_config(tempdir_factory, store):
    path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(path):
        remove_config_from_repo(path)
        ret = install(
            C.CONFIG_FILE, store, hook_types=['pre-commit'],
            overwrite=True, skip_on_missing_config=False,
        )
        assert ret == 0

        env = dict(os.environ, PRE_COMMIT_ALLOW_NO_CONFIG='1')
        ret, output = _get_commit_output(tempdir_factory, env=env)
        assert ret == 0
        expected = (
            '`.pre-commit-config.yaml` config file not found. '
            'Skipping `pre-commit`.'
        )
        assert expected in output
