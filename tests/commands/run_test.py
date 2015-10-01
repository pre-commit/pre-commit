# -*- coding: UTF-8 -*-
from __future__ import unicode_literals

import functools
import io
import os
import os.path
import subprocess
import sys

import mock
import pytest

from pre_commit.commands.install_uninstall import install
from pre_commit.commands.run import _get_skips
from pre_commit.commands.run import _has_unmerged_paths
from pre_commit.commands.run import get_changed_files
from pre_commit.commands.run import run
from pre_commit.ordereddict import OrderedDict
from pre_commit.output import sys_stdout_write_wrapper
from pre_commit.runner import Runner
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import add_config_to_repo
from testing.fixtures import make_consuming_repo


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


def stage_a_file():
    cmd_output('touch', 'foo.py')
    cmd_output('git', 'add', 'foo.py')


def get_write_mock_output(write_mock):
    return b''.join(call[0][0] for call in write_mock.write.call_args_list)


def _get_opts(
        all_files=False,
        files=(),
        color=False,
        verbose=False,
        hook=None,
        no_stash=False,
        origin='',
        source='',
        allow_unstaged_config=False,
):
    # These are mutually exclusive
    assert not (all_files and files)
    return auto_namedtuple(
        all_files=all_files,
        files=files,
        color=color,
        verbose=verbose,
        hook=hook,
        no_stash=no_stash,
        origin=origin,
        source=source,
        allow_unstaged_config=allow_unstaged_config,
    )


def _do_run(repo, args, environ={}):
    runner = Runner(repo)
    write_mock = mock.Mock()
    write_fn = functools.partial(sys_stdout_write_wrapper, stream=write_mock)
    ret = run(runner, args, write=write_fn, environ=environ)
    printed = get_write_mock_output(write_mock)
    return ret, printed


def _test_run(repo, options, expected_outputs, expected_ret, stage):
    if stage:
        stage_a_file()
    args = _get_opts(**options)
    ret, printed = _do_run(repo, args)
    assert ret == expected_ret, (ret, expected_ret, printed)
    for expected_output_part in expected_outputs:
        assert expected_output_part in printed


def test_run_all_hooks_failing(
        repo_with_failing_hook, mock_out_store_directory
):
    _test_run(
        repo_with_failing_hook,
        {},
        (
            b'Failing hook',
            b'Failed',
            b'hookid: failing_hook',
            b'Fail\nfoo.py\n',
        ),
        1,
        True,
    )


def test_arbitrary_bytes_hook(tempdir_factory, mock_out_store_directory):
    git_path = make_consuming_repo(tempdir_factory, 'arbitrary_bytes_repo')
    with cwd(git_path):
        _test_run(git_path, {}, (b'\xe2\x98\x83\xb2\n',), 1, True)


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
    )
)
def test_run(
        repo_with_passing_hook,
        options,
        outputs,
        expected_ret,
        stage,
        mock_out_store_directory,
):
    _test_run(repo_with_passing_hook, options, outputs, expected_ret, stage)


@pytest.mark.parametrize(
    ('origin', 'source', 'expect_failure'),
    (
        ('master', 'master', False),
        ('master', '', True),
        ('', 'master', True),
    )
)
def test_origin_source_error_msg(
        repo_with_passing_hook, origin, source, expect_failure,
        mock_out_store_directory,
):
    args = _get_opts(origin=origin, source=source)
    ret, printed = _do_run(repo_with_passing_hook, args)
    warning_msg = b'Specify both --origin and --source.'
    if expect_failure:
        assert ret == 1
        assert warning_msg in printed
    else:
        assert ret == 0
        assert warning_msg not in printed


@pytest.mark.parametrize(
    ('no_stash', 'all_files', 'expect_stash'),
    (
        (True, True, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
    ),
)
def test_no_stash(
        repo_with_passing_hook,
        no_stash,
        all_files,
        expect_stash,
        mock_out_store_directory,
):
    stage_a_file()
    # Make unstaged changes
    with open('foo.py', 'w') as foo_file:
        foo_file.write('import os\n')

    args = _get_opts(no_stash=no_stash, all_files=all_files)
    ret, printed = _do_run(repo_with_passing_hook, args)
    assert ret == 0
    warning_msg = b'[WARNING] Unstaged files detected.'
    if expect_stash:
        assert warning_msg in printed
    else:
        assert warning_msg not in printed


@pytest.mark.parametrize(('output', 'expected'), (('some', True), ('', False)))
def test_has_unmerged_paths(output, expected):
    mock_runner = mock.Mock()
    mock_runner.cmd_runner.run.return_value = (1, output, '')
    assert _has_unmerged_paths(mock_runner) is expected


def test_merge_conflict(in_merge_conflict, mock_out_store_directory):
    ret, printed = _do_run(in_merge_conflict, _get_opts())
    assert ret == 1
    assert b'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_modified(in_merge_conflict, mock_out_store_directory):
    # Touch another file so we have unstaged non-conflicting things
    assert os.path.exists('dummy')
    with open('dummy', 'w') as dummy_file:
        dummy_file.write('bar\nbaz\n')

    ret, printed = _do_run(in_merge_conflict, _get_opts())
    assert ret == 1
    assert b'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_resolved(in_merge_conflict, mock_out_store_directory):
    cmd_output('git', 'add', '.')
    ret, printed = _do_run(in_merge_conflict, _get_opts())
    for msg in (
            b'Checking merge-conflict files only.', b'Bash hook', b'Passed',
    ):
        assert msg in printed


@pytest.mark.parametrize(
    ('environ', 'expected_output'),
    (
        ({}, set([])),
        ({'SKIP': ''}, set([])),
        ({'SKIP': ','}, set([])),
        ({'SKIP': ',foo'}, set(['foo'])),
        ({'SKIP': 'foo'}, set(['foo'])),
        ({'SKIP': 'foo,bar'}, set(['foo', 'bar'])),
        ({'SKIP': ' foo , bar'}, set(['foo', 'bar'])),
    ),
)
def test_get_skips(environ, expected_output):
    ret = _get_skips(environ)
    assert ret == expected_output


def test_skip_hook(repo_with_passing_hook, mock_out_store_directory):
    ret, printed = _do_run(
        repo_with_passing_hook, _get_opts(), {'SKIP': 'bash_hook'},
    )
    for msg in (b'Bash hook', b'Skipped'):
        assert msg in printed


def test_hook_id_not_in_non_verbose_output(
        repo_with_passing_hook, mock_out_store_directory
):
    ret, printed = _do_run(repo_with_passing_hook, _get_opts(verbose=False))
    assert b'[bash_hook]' not in printed


def test_hook_id_in_verbose_output(
        repo_with_passing_hook, mock_out_store_directory,
):
    ret, printed = _do_run(repo_with_passing_hook, _get_opts(verbose=True))
    assert b'[bash_hook] Bash hook' in printed


def test_multiple_hooks_same_id(
        repo_with_passing_hook, mock_out_store_directory,
):
    with cwd(repo_with_passing_hook):
        # Add bash hook on there again
        with io.open('.pre-commit-config.yaml', 'a+') as config_file:
            config_file.write('    - id: bash_hook\n')
        cmd_output('git', 'add', '.pre-commit-config.yaml')
        stage_a_file()

    ret, output = _do_run(repo_with_passing_hook, _get_opts())
    assert ret == 0
    assert output.count(b'Bash hook') == 2


def test_non_ascii_hook_id(
        repo_with_passing_hook, mock_out_store_directory, tempdir_factory,
):
    with cwd(repo_with_passing_hook):
        install(Runner(repo_with_passing_hook))
        # Don't want to write to home directory
        env = dict(os.environ, PRE_COMMIT_HOME=tempdir_factory.get())
        _, stdout, _ = cmd_output(
            sys.executable, '-m', 'pre_commit.main', 'run', '☃',
            env=env, retcode=None,
        )
        assert 'UnicodeDecodeError' not in stdout
        # Doesn't actually happen, but a reasonable assertion
        assert 'UnicodeEncodeError' not in stdout


def test_stdout_write_bug_py26(
        repo_with_failing_hook, mock_out_store_directory, tempdir_factory,
):
    with cwd(repo_with_failing_hook):
        # Add bash hook on there again
        with io.open(
            '.pre-commit-config.yaml', 'a+', encoding='UTF-8',
        ) as config_file:
            config_file.write('        args: ["☃"]\n')
        cmd_output('git', 'add', '.pre-commit-config.yaml')
        stage_a_file()

        install(Runner(repo_with_failing_hook))

        # Don't want to write to home directory
        env = dict(os.environ, PRE_COMMIT_HOME=tempdir_factory.get())
        # Have to use subprocess because pytest monkeypatches sys.stdout
        _, stdout, _ = cmd_output(
            'git', 'commit', '-m', 'Commit!',
            # git commit puts pre-commit to stderr
            stderr=subprocess.STDOUT,
            env=env,
            retcode=None,
        )
        assert 'UnicodeEncodeError' not in stdout
        # Doesn't actually happen, but a reasonable assertion
        assert 'UnicodeDecodeError' not in stdout


def test_get_changed_files():
    files = get_changed_files(
        '78c682a1d13ba20e7cb735313b9314a74365cd3a',
        '3387edbb1288a580b37fe25225aa0b856b18ad1a',
    )
    assert files == ['CHANGELOG.md', 'setup.py']


def test_lots_of_files(mock_out_store_directory, tempdir_factory):
    # windows xargs seems to have a bug, here's a regression test for
    # our workaround
    git_path = make_consuming_repo(tempdir_factory, 'python_hooks_repo')
    with cwd(git_path):
        # Override files so we run against them
        with io.open('.pre-commit-config.yaml', 'a+') as config_file:
            config_file.write('        files: ""\n')

        # Write a crap ton of files
        for i in range(400):
            filename = '{0}{1}'.format('a' * 100, i)
            open(filename, 'w').close()

        cmd_output('bash', '-c', 'git add .')
        install(Runner(git_path))

        # Don't want to write to home directory
        env = dict(os.environ, PRE_COMMIT_HOME=tempdir_factory.get())
        cmd_output(
            'git', 'commit', '-m', 'Commit!',
            # git commit puts pre-commit to stderr
            stderr=subprocess.STDOUT,
            env=env,
        )


def test_local_hook_passes(
        repo_with_passing_hook, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'local'),
        ('hooks', (OrderedDict((
            ('id', 'pylint'),
            ('name', 'PyLint'),
            ('entry', 'python -m pylint.__main__'),
            ('language', 'system'),
            ('files', r'\.py$'),
        )), OrderedDict((
            ('id', 'do_not_commit'),
            ('name', 'Block if "DO NOT COMMIT" is found'),
            ('entry', 'DO NOT COMMIT'),
            ('language', 'pcre'),
            ('files', '^(.*)$'),
        ))))
    ))
    add_config_to_repo(repo_with_passing_hook, config)

    with io.open('dummy.py', 'w') as staged_file:
        staged_file.write('"""TODO: something"""\n')
    cmd_output('git', 'add', 'dummy.py')

    _test_run(
        repo_with_passing_hook,
        options={},
        expected_outputs=[b''],
        expected_ret=0,
        stage=False
    )


def test_local_hook_fails(
        repo_with_passing_hook, mock_out_store_directory,
):
    config = OrderedDict((
        ('repo', 'local'),
        ('hooks', [OrderedDict((
            ('id', 'no-todo'),
            ('name', 'No TODO'),
            ('entry', 'grep -iI todo'),
            ('expected_return_value', 1),
            ('language', 'system'),
            ('files', ''),
        ))])
    ))
    add_config_to_repo(repo_with_passing_hook, config)

    with io.open('dummy.py', 'w') as staged_file:
        staged_file.write('"""TODO: something"""\n')
    cmd_output('git', 'add', 'dummy.py')

    _test_run(
        repo_with_passing_hook,
        options={},
        expected_outputs=[b''],
        expected_ret=1,
        stage=False
    )


def test_allow_unstaged_config_option(
        repo_with_passing_hook, mock_out_store_directory,
):
    with cwd(repo_with_passing_hook):
        with io.open('.pre-commit-config.yaml', 'a+') as config_file:
            # writing a newline should be relatively harmless to get a change
            config_file.write('\n')

    args = _get_opts(allow_unstaged_config=True)
    ret, printed = _do_run(repo_with_passing_hook, args)
    assert b'You have an unstaged config file' in printed
    assert b'have specified the --allow-unstaged-config option.' in printed
    assert ret == 0


def modify_config(path):
    with cwd(path):
        with io.open('.pre-commit-config.yaml', 'a+') as config_file:
            # writing a newline should be relatively harmless to get a change
            config_file.write('\n')


def test_no_allow_unstaged_config_option(
    repo_with_passing_hook, mock_out_store_directory,
):
    modify_config(repo_with_passing_hook)
    args = _get_opts(allow_unstaged_config=False)
    ret, printed = _do_run(repo_with_passing_hook, args)
    assert b'Your .pre-commit-config.yaml is unstaged.' in printed
    assert ret == 1


def test_no_stash_suppresses_allow_unstaged_config_option(
        repo_with_passing_hook, mock_out_store_directory,
):
    modify_config(repo_with_passing_hook)
    args = _get_opts(allow_unstaged_config=False, no_stash=True)
    ret, printed = _do_run(repo_with_passing_hook, args)
    assert b'Your .pre-commit-config.yaml is unstaged.' not in printed


def test_all_files_suppresses_allow_unstaged_config_option(
        repo_with_passing_hook, mock_out_store_directory,
):
    modify_config(repo_with_passing_hook)
    args = _get_opts(all_files=True)
    ret, printed = _do_run(repo_with_passing_hook, args)
    assert b'Your .pre-commit-config.yaml is unstaged.' not in printed


def test_files_suppresses_allow_unstaged_config_option(
        repo_with_passing_hook, mock_out_store_directory,
):
    modify_config(repo_with_passing_hook)
    args = _get_opts(files=['.pre-commit-config.yaml'])
    ret, printed = _do_run(repo_with_passing_hook, args)
    assert b'Your .pre-commit-config.yaml is unstaged.' not in printed
