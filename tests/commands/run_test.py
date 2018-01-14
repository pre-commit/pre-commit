# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

import io
import os.path
import subprocess
import sys
from collections import OrderedDict

import pytest

import pre_commit.constants as C
from pre_commit.commands.install_uninstall import install
from pre_commit.commands.run import _compute_cols
from pre_commit.commands.run import _filter_by_include_exclude
from pre_commit.commands.run import _get_skips
from pre_commit.commands.run import _has_unmerged_paths
from pre_commit.commands.run import run
from pre_commit.runner import Runner
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from pre_commit.util import make_executable
from testing.fixtures import add_config_to_repo
from testing.fixtures import make_consuming_repo
from testing.fixtures import modify_config
from testing.fixtures import read_config
from testing.util import cmd_output_mocked_pre_commit_home
from testing.util import run_opts
from testing.util import xfailif_no_symlink


@pytest.yield_fixture
def repo_with_passing_hook(tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(git_path):
        yield git_path


@pytest.yield_fixture
def repo_with_failing_hook(tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'failing_hook_repo')
    with cwd(git_path):
        yield git_path


def stage_a_file(filename='foo.py'):
    open(filename, 'a').close()
    cmd_output('git', 'add', filename)


def _do_run(cap_out, repo, args, environ={}, config_file=C.CONFIG_FILE):
    runner = Runner(repo, config_file)
    with cwd(runner.git_root):  # replicates Runner.create behaviour
        ret = run(runner, args, environ=environ)
    printed = cap_out.get_bytes()
    return ret, printed


def _test_run(
    cap_out, repo, opts, expected_outputs, expected_ret, stage,
    config_file=C.CONFIG_FILE,
):
    if stage:
        stage_a_file()
    args = run_opts(**opts)
    ret, printed = _do_run(cap_out, repo, args, config_file=config_file)

    assert ret == expected_ret, (ret, expected_ret, printed)
    for expected_output_part in expected_outputs:
        assert expected_output_part in printed


def test_run_all_hooks_failing(
        cap_out, repo_with_failing_hook, mock_out_store_directory,
):
    _test_run(
        cap_out,
        repo_with_failing_hook,
        {},
        (
            b'Failing hook',
            b'Failed',
            b'hookid: failing_hook',
            b'Fail\nfoo.py\n',
        ),
        expected_ret=1,
        stage=True,
    )


def test_arbitrary_bytes_hook(
        cap_out, tempdir_factory, mock_out_store_directory,
):
    git_path = make_consuming_repo(tempdir_factory, 'arbitrary_bytes_repo')
    with cwd(git_path):
        _test_run(cap_out, git_path, {}, (b'\xe2\x98\x83\xb2\n',), 1, True)


def test_hook_that_modifies_but_returns_zero(
        cap_out, tempdir_factory, mock_out_store_directory,
):
    git_path = make_consuming_repo(
        tempdir_factory, 'modified_file_returns_zero_repo',
    )
    with cwd(git_path):
        stage_a_file('bar.py')
        _test_run(
            cap_out,
            git_path,
            {},
            (
                # The first should fail
                b'Failed',
                # With a modified file (default message + the hook's output)
                b'Files were modified by this hook. Additional output:\n\n'
                b'Modified: foo.py',
                # The next hook should pass despite the first modifying
                b'Passed',
                # The next hook should fail
                b'Failed',
                # bar.py was modified, but provides no additional output
                b'Files were modified by this hook.\n',
            ),
            1,
            True,
        )


def test_types_hook_repository(
        cap_out, tempdir_factory, mock_out_store_directory,
):
    git_path = make_consuming_repo(tempdir_factory, 'types_repo')
    with cwd(git_path):
        stage_a_file('bar.py')
        stage_a_file('bar.notpy')
        ret, printed = _do_run(cap_out, git_path, run_opts())
        assert ret == 1
        assert b'bar.py' in printed
        assert b'bar.notpy' not in printed


def test_exclude_types_hook_repository(
        cap_out, tempdir_factory, mock_out_store_directory,
):
    git_path = make_consuming_repo(tempdir_factory, 'exclude_types_repo')
    with cwd(git_path):
        with io.open('exe', 'w') as exe:
            exe.write('#!/usr/bin/env python3\n')
        make_executable('exe')
        cmd_output('git', 'add', 'exe')
        stage_a_file('bar.py')
        ret, printed = _do_run(cap_out, git_path, run_opts())
        assert ret == 1
        assert b'bar.py' in printed
        assert b'exe' not in printed


def test_global_exclude(cap_out, tempdir_factory, mock_out_store_directory):
    git_path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(git_path):
        with modify_config() as config:
            config['exclude'] = '^foo.py$'
        open('foo.py', 'a').close()
        open('bar.py', 'a').close()
        cmd_output('git', 'add', '.')
        ret, printed = _do_run(cap_out, git_path, run_opts(verbose=True))
        assert ret == 0
        # Does not contain foo.py since it was excluded
        expected = b'hookid: bash_hook\n\nbar.py\nHello World\n\n'
        assert printed.endswith(expected)


def test_show_diff_on_failure(
        capfd, cap_out, tempdir_factory, mock_out_store_directory,
):
    git_path = make_consuming_repo(
        tempdir_factory, 'modified_file_returns_zero_repo',
    )
    with cwd(git_path):
        stage_a_file('bar.py')
        _test_run(
            cap_out, git_path, {'show_diff_on_failure': True},
            # we're only testing the output after running
            (), 1, True,
        )
    out, _ = capfd.readouterr()
    assert 'diff --git' in out


@pytest.mark.parametrize(
    ('options', 'outputs', 'expected_ret', 'stage'),
    (
        ({}, (b'Bash hook', b'Passed'), 0, True),
        ({'verbose': True}, (b'foo.py\nHello World',), 0, True),
        ({'hook': 'bash_hook'}, (b'Bash hook', b'Passed'), 0, True),
        ({'hook': 'nope'}, (b'No hook with id `nope`',), 1, True),
        (
            {'all_files': True, 'verbose': True},
            (b'foo.py',),
            0,
            True,
        ),
        (
            {'files': ('foo.py',), 'verbose': True},
            (b'foo.py',),
            0,
            True,
        ),
        ({}, (b'Bash hook', b'(no files to check)', b'Skipped'), 0, False),
    ),
)
def test_run(
        cap_out,
        repo_with_passing_hook,
        options,
        outputs,
        expected_ret,
        stage,
        mock_out_store_directory,
):
    _test_run(
        cap_out,
        repo_with_passing_hook,
        options,
        outputs,
        expected_ret,
        stage,
    )


def test_run_output_logfile(
        cap_out,
        tempdir_factory,
        mock_out_store_directory,
):

    expected_output = (
        b'This is STDOUT output\n',
        b'This is STDERR output\n',
    )

    git_path = make_consuming_repo(tempdir_factory, 'logfile_repo')
    with cwd(git_path):
        _test_run(
            cap_out,
            git_path, {},
            expected_output,
            expected_ret=1,
            stage=True,
        )
    logfile_path = os.path.join(git_path, 'test.log')
    assert os.path.exists(logfile_path)
    with open(logfile_path, 'rb') as logfile:
        logfile_content = logfile.readlines()

    for expected_output_part in expected_output:
        assert expected_output_part in logfile_content


def test_always_run(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    with modify_config() as config:
        config['repos'][0]['hooks'][0]['always_run'] = True
    _test_run(
        cap_out,
        repo_with_passing_hook,
        {},
        (b'Bash hook', b'Passed'),
        0,
        stage=False,
    )


def test_always_run_alt_config(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    repo_root = '.'
    config = read_config(repo_root)
    config['repos'][0]['hooks'][0]['always_run'] = True
    alt_config_file = 'alternate_config.yaml'
    add_config_to_repo(repo_root, config, config_file=alt_config_file)

    _test_run(
        cap_out,
        repo_with_passing_hook,
        {},
        (b'Bash hook', b'Passed'),
        0,
        stage=False,
        config_file=alt_config_file,
    )


@pytest.mark.parametrize(
    ('origin', 'source', 'expect_failure'),
    (
        ('master', 'master', False),
        ('master', '', True),
        ('', 'master', True),
    ),
)
def test_origin_source_error_msg(
        repo_with_passing_hook, origin, source, expect_failure,
        mock_out_store_directory, cap_out,
):
    args = run_opts(origin=origin, source=source)
    ret, printed = _do_run(cap_out, repo_with_passing_hook, args)
    warning_msg = b'Specify both --origin and --source.'
    if expect_failure:
        assert ret == 1
        assert warning_msg in printed
    else:
        assert ret == 0
        assert warning_msg not in printed


def test_has_unmerged_paths(in_merge_conflict):
    assert _has_unmerged_paths() is True
    cmd_output('git', 'add', '.')
    assert _has_unmerged_paths() is False


def test_merge_conflict(cap_out, in_merge_conflict, mock_out_store_directory):
    ret, printed = _do_run(cap_out, in_merge_conflict, run_opts())
    assert ret == 1
    assert b'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_modified(
        cap_out, in_merge_conflict, mock_out_store_directory,
):
    # Touch another file so we have unstaged non-conflicting things
    assert os.path.exists('dummy')
    with open('dummy', 'w') as dummy_file:
        dummy_file.write('bar\nbaz\n')

    ret, printed = _do_run(cap_out, in_merge_conflict, run_opts())
    assert ret == 1
    assert b'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_resolved(
        cap_out, in_merge_conflict, mock_out_store_directory,
):
    cmd_output('git', 'add', '.')
    ret, printed = _do_run(cap_out, in_merge_conflict, run_opts())
    for msg in (
            b'Checking merge-conflict files only.', b'Bash hook', b'Passed',
    ):
        assert msg in printed


@pytest.mark.parametrize(
    ('hooks', 'verbose', 'expected'),
    (
        ([], True, 80),
        ([{'id': 'a', 'name': 'a' * 51}], False, 81),
        ([{'id': 'a', 'name': 'a' * 51}], True, 85),
        (
            [{'id': 'a', 'name': 'a' * 51}, {'id': 'b', 'name': 'b' * 52}],
            False,
            82,
        ),
    ),
)
def test_compute_cols(hooks, verbose, expected):
    assert _compute_cols(hooks, verbose) == expected


@pytest.mark.parametrize(
    ('environ', 'expected_output'),
    (
        ({}, set()),
        ({'SKIP': ''}, set()),
        ({'SKIP': ','}, set()),
        ({'SKIP': ',foo'}, {'foo'}),
        ({'SKIP': 'foo'}, {'foo'}),
        ({'SKIP': 'foo,bar'}, {'foo', 'bar'}),
        ({'SKIP': ' foo , bar'}, {'foo', 'bar'}),
    ),
)
def test_get_skips(environ, expected_output):
    ret = _get_skips(environ)
    assert ret == expected_output


def test_skip_hook(cap_out, repo_with_passing_hook, mock_out_store_directory):
    ret, printed = _do_run(
        cap_out, repo_with_passing_hook, run_opts(), {'SKIP': 'bash_hook'},
    )
    for msg in (b'Bash hook', b'Skipped'):
        assert msg in printed


def test_hook_id_not_in_non_verbose_output(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    ret, printed = _do_run(
        cap_out, repo_with_passing_hook, run_opts(verbose=False),
    )
    assert b'[bash_hook]' not in printed


def test_hook_id_in_verbose_output(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    ret, printed = _do_run(
        cap_out, repo_with_passing_hook, run_opts(verbose=True),
    )
    assert b'[bash_hook] Bash hook' in printed


def test_multiple_hooks_same_id(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    with cwd(repo_with_passing_hook):
        # Add bash hook on there again
        with modify_config() as config:
            config['repos'][0]['hooks'].append({'id': 'bash_hook'})
        stage_a_file()

    ret, output = _do_run(cap_out, repo_with_passing_hook, run_opts())
    assert ret == 0
    assert output.count(b'Bash hook') == 2


def test_non_ascii_hook_id(
        repo_with_passing_hook, mock_out_store_directory, tempdir_factory,
):
    with cwd(repo_with_passing_hook):
        install(Runner(repo_with_passing_hook, C.CONFIG_FILE))
        _, stdout, _ = cmd_output_mocked_pre_commit_home(
            sys.executable, '-m', 'pre_commit.main', 'run', '☃',
            retcode=None, tempdir_factory=tempdir_factory,
        )
        assert 'UnicodeDecodeError' not in stdout
        # Doesn't actually happen, but a reasonable assertion
        assert 'UnicodeEncodeError' not in stdout


def test_stdout_write_bug_py26(
        repo_with_failing_hook, mock_out_store_directory, tempdir_factory,
):
    with cwd(repo_with_failing_hook):
        with modify_config() as config:
            config['repos'][0]['hooks'][0]['args'] = ['☃']
        stage_a_file()

        install(Runner(repo_with_failing_hook, C.CONFIG_FILE))

        # Have to use subprocess because pytest monkeypatches sys.stdout
        _, stdout, _ = cmd_output_mocked_pre_commit_home(
            'git', 'commit', '-m', 'Commit!',
            # git commit puts pre-commit to stderr
            stderr=subprocess.STDOUT,
            retcode=None,
            tempdir_factory=tempdir_factory,
        )
        assert 'UnicodeEncodeError' not in stdout
        # Doesn't actually happen, but a reasonable assertion
        assert 'UnicodeDecodeError' not in stdout


def test_hook_install_failure(mock_out_store_directory, tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'not_installable_repo')
    with cwd(git_path):
        install(Runner(git_path, C.CONFIG_FILE))

        _, stdout, _ = cmd_output_mocked_pre_commit_home(
            'git', 'commit', '-m', 'Commit!',
            # git commit puts pre-commit to stderr
            stderr=subprocess.STDOUT,
            retcode=None,
            encoding=None,
            tempdir_factory=tempdir_factory,
        )
        assert b'UnicodeDecodeError' not in stdout
        # Doesn't actually happen, but a reasonable assertion
        assert b'UnicodeEncodeError' not in stdout

        # Sanity check our output
        assert (
            b'An unexpected error has occurred: CalledProcessError: ' in
            stdout
        )
        assert '☃'.encode('UTF-8') + '²'.encode('latin1') in stdout


def test_lots_of_files(mock_out_store_directory, tempdir_factory):
    # windows xargs seems to have a bug, here's a regression test for
    # our workaround
    git_path = make_consuming_repo(tempdir_factory, 'python_hooks_repo')
    with cwd(git_path):
        # Override files so we run against them
        with modify_config() as config:
            config['repos'][0]['hooks'][0]['files'] = ''

        # Write a crap ton of files
        for i in range(400):
            filename = '{}{}'.format('a' * 100, i)
            open(filename, 'w').close()

        cmd_output('bash', '-c', 'git add .')
        install(Runner(git_path, C.CONFIG_FILE))

        cmd_output_mocked_pre_commit_home(
            'git', 'commit', '-m', 'Commit!',
            # git commit puts pre-commit to stderr
            stderr=subprocess.STDOUT,
            tempdir_factory=tempdir_factory,
        )


def test_push_hook(cap_out, repo_with_passing_hook, mock_out_store_directory):
    config = OrderedDict((
        ('repo', 'local'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'flake8'),
                    ('name', 'hook 1'),
                    ('entry', "'{}' -m flake8".format(sys.executable)),
                    ('language', 'system'),
                    ('types', ['python']),
                    ('stages', ['commit']),
                )),
                OrderedDict((
                    ('id', 'do_not_commit'),
                    ('name', 'hook 2'),
                    ('entry', 'DO NOT COMMIT'),
                    ('language', 'pygrep'),
                    ('types', ['text']),
                    ('stages', ['push']),
                )),
            ),
        ),
    ))
    add_config_to_repo(repo_with_passing_hook, config)

    open('dummy.py', 'a').close()
    cmd_output('git', 'add', 'dummy.py')

    _test_run(
        cap_out,
        repo_with_passing_hook,
        {'hook_stage': 'commit'},
        expected_outputs=[b'hook 1'],
        expected_ret=0,
        stage=False,
    )

    _test_run(
        cap_out,
        repo_with_passing_hook,
        {'hook_stage': 'push'},
        expected_outputs=[b'hook 2'],
        expected_ret=0,
        stage=False,
    )


def test_commit_msg_hook(cap_out, commit_msg_repo, mock_out_store_directory):
    filename = '.git/COMMIT_EDITMSG'
    with io.open(filename, 'w') as f:
        f.write('This is the commit message')

    _test_run(
        cap_out,
        commit_msg_repo,
        {'hook_stage': 'commit-msg', 'commit_msg_filename': filename},
        expected_outputs=[b'Must have "Signed off by:"', b'Failed'],
        expected_ret=1,
        stage=False,
    )


def test_local_hook_passes(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'local'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'flake8'),
                    ('name', 'flake8'),
                    ('entry', "'{}' -m flake8".format(sys.executable)),
                    ('language', 'system'),
                    ('files', r'\.py$'),
                )), OrderedDict((
                    ('id', 'do_not_commit'),
                    ('name', 'Block if "DO NOT COMMIT" is found'),
                    ('entry', 'DO NOT COMMIT'),
                    ('language', 'pygrep'),
                    ('files', '^(.*)$'),
                )),
            ),
        ),
    ))
    add_config_to_repo(repo_with_passing_hook, config)

    with io.open('dummy.py', 'w') as staged_file:
        staged_file.write('"""TODO: something"""\n')
    cmd_output('git', 'add', 'dummy.py')

    _test_run(
        cap_out,
        repo_with_passing_hook,
        opts={},
        expected_outputs=[b''],
        expected_ret=0,
        stage=False,
    )


def test_local_hook_fails(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'local'),
        (
            'hooks', [OrderedDict((
                ('id', 'no-todo'),
                ('name', 'No TODO'),
                ('entry', 'sh -c "! grep -iI todo $@" --'),
                ('language', 'system'),
                ('files', ''),
            ))],
        ),
    ))
    add_config_to_repo(repo_with_passing_hook, config)

    with io.open('dummy.py', 'w') as staged_file:
        staged_file.write('"""TODO: something"""\n')
    cmd_output('git', 'add', 'dummy.py')

    _test_run(
        cap_out,
        repo_with_passing_hook,
        opts={},
        expected_outputs=[b''],
        expected_ret=1,
        stage=False,
    )


def test_pcre_deprecation_warning(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'local'),
        (
            'hooks', [OrderedDict((
                ('id', 'pcre-hook'),
                ('name', 'pcre-hook'),
                ('language', 'pcre'),
                ('entry', '.'),
            ))],
        ),
    ))
    add_config_to_repo(repo_with_passing_hook, config)

    _test_run(
        cap_out,
        repo_with_passing_hook,
        opts={},
        expected_outputs=[
            b'[WARNING] `pcre-hook` (from local) uses the deprecated '
            b'pcre language.',
        ],
        expected_ret=0,
        stage=False,
    )


def test_meta_hook_passes(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'meta'),
        (
            'hooks', (
                OrderedDict((
                    ('id', 'check-useless-excludes'),
                )),
            ),
        ),
    ))
    add_config_to_repo(repo_with_passing_hook, config)

    _test_run(
        cap_out,
        repo_with_passing_hook,
        opts={},
        expected_outputs=[b'Check for useless excludes'],
        expected_ret=0,
        stage=False,
    )


@pytest.yield_fixture
def modified_config_repo(repo_with_passing_hook):
    with modify_config(repo_with_passing_hook, commit=False) as config:
        # Some minor modification
        config['repos'][0]['hooks'][0]['files'] = ''
    yield repo_with_passing_hook


def test_error_with_unstaged_config(
        cap_out, modified_config_repo, mock_out_store_directory,
):
    args = run_opts()
    ret, printed = _do_run(cap_out, modified_config_repo, args)
    assert b'Your pre-commit configuration is unstaged.' in printed
    assert ret == 1


@pytest.mark.parametrize(
    'opts', ({'all_files': True}, {'files': [C.CONFIG_FILE]}),
)
def test_no_unstaged_error_with_all_files_or_files(
        cap_out, modified_config_repo, mock_out_store_directory, opts,
):
    args = run_opts(**opts)
    ret, printed = _do_run(cap_out, modified_config_repo, args)
    assert b'Your pre-commit configuration is unstaged.' not in printed


def test_files_running_subdir(
        repo_with_passing_hook, mock_out_store_directory, tempdir_factory,
):
    with cwd(repo_with_passing_hook):
        install(Runner(repo_with_passing_hook, C.CONFIG_FILE))

        os.mkdir('subdir')
        open('subdir/foo.py', 'w').close()
        cmd_output('git', 'add', 'subdir/foo.py')

        with cwd('subdir'):
            # Use subprocess to demonstrate behaviour in main
            _, stdout, _ = cmd_output_mocked_pre_commit_home(
                sys.executable, '-m', 'pre_commit.main', 'run', '-v',
                # Files relative to where we are (#339)
                '--files', 'foo.py',
                tempdir_factory=tempdir_factory,
            )
        assert 'subdir/foo.py'.replace('/', os.sep) in stdout


@pytest.mark.parametrize(
    ('pass_filenames', 'hook_args', 'expected_out'),
    (
        (True, [], b'foo.py'),
        (False, [], b''),
        (True, ['some', 'args'], b'some args foo.py'),
        (False, ['some', 'args'], b'some args'),
    ),
)
def test_pass_filenames(
        cap_out, repo_with_passing_hook, mock_out_store_directory,
        pass_filenames,
        hook_args,
        expected_out,
):
    with modify_config() as config:
        config['repos'][0]['hooks'][0]['pass_filenames'] = pass_filenames
        config['repos'][0]['hooks'][0]['args'] = hook_args
    stage_a_file()
    ret, printed = _do_run(
        cap_out, repo_with_passing_hook, run_opts(verbose=True),
    )
    assert expected_out + b'\nHello World' in printed
    assert (b'foo.py' in printed) == pass_filenames


def test_fail_fast(
        cap_out, repo_with_failing_hook, mock_out_store_directory,
):
    with cwd(repo_with_failing_hook):
        with modify_config() as config:
            # More than one hook
            config['fail_fast'] = True
            config['repos'][0]['hooks'] *= 2
        stage_a_file()

        ret, printed = _do_run(cap_out, repo_with_failing_hook, run_opts())
        # it should have only run one hook
        assert printed.count(b'Failing hook') == 1


@pytest.fixture
def some_filenames():
    return (
        '.pre-commit-hooks.yaml',
        'pre_commit/main.py',
        'pre_commit/git.py',
        'im_a_file_that_doesnt_exist.py',
    )


def test_include_exclude_base_case(some_filenames):
    ret = _filter_by_include_exclude(some_filenames, '', '^$')
    assert ret == {
        '.pre-commit-hooks.yaml',
        'pre_commit/main.py',
        'pre_commit/git.py',
    }


@xfailif_no_symlink
def test_matches_broken_symlink(tmpdir):  # pramga: no cover (non-windows)
    with tmpdir.as_cwd():
        os.symlink('does-not-exist', 'link')
        ret = _filter_by_include_exclude({'link'}, '', '^$')
        assert ret == {'link'}


def test_include_exclude_total_match(some_filenames):
    ret = _filter_by_include_exclude(some_filenames, r'^.*\.py$', '^$')
    assert ret == {'pre_commit/main.py', 'pre_commit/git.py'}


def test_include_exclude_does_search_instead_of_match(some_filenames):
    ret = _filter_by_include_exclude(some_filenames, r'\.yaml$', '^$')
    assert ret == {'.pre-commit-hooks.yaml'}


def test_include_exclude_exclude_removes_files(some_filenames):
    ret = _filter_by_include_exclude(some_filenames, '', r'\.py$')
    assert ret == {'.pre-commit-hooks.yaml'}
