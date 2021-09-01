import os.path
import shlex
import sys
import time
from typing import MutableMapping
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import color
from pre_commit.commands.install_uninstall import install
from pre_commit.commands.run import _compute_cols
from pre_commit.commands.run import _full_msg
from pre_commit.commands.run import _get_skips
from pre_commit.commands.run import _has_unmerged_paths
from pre_commit.commands.run import _start_msg
from pre_commit.commands.run import Classifier
from pre_commit.commands.run import filter_by_include_exclude
from pre_commit.commands.run import run
from pre_commit.util import cmd_output
from pre_commit.util import make_executable
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import add_config_to_repo
from testing.fixtures import git_dir
from testing.fixtures import make_consuming_repo
from testing.fixtures import modify_config
from testing.fixtures import read_config
from testing.fixtures import sample_meta_config
from testing.fixtures import write_config
from testing.util import cmd_output_mocked_pre_commit_home
from testing.util import cwd
from testing.util import git_commit
from testing.util import run_opts


def test_start_msg():
    ret = _start_msg(start='start', end_len=5, cols=15)
    # 4 dots: 15 - 5 - 5 - 1
    assert ret == 'start....'


def test_full_msg():
    ret = _full_msg(
        start='start',
        end_msg='end',
        end_color='',
        use_color=False,
        cols=15,
    )
    # 6 dots: 15 - 5 - 3 - 1
    assert ret == 'start......end\n'


def test_full_msg_with_cjk():
    ret = _full_msg(
        start='啊あ아',
        end_msg='end',
        end_color='',
        use_color=False,
        cols=15,
    )
    # 5 dots: 15 - 6 - 3 - 1
    assert ret == '啊あ아.....end\n'


def test_full_msg_with_color():
    ret = _full_msg(
        start='start',
        end_msg='end',
        end_color=color.RED,
        use_color=True,
        cols=15,
    )
    # 6 dots: 15 - 5 - 3 - 1
    assert ret == f'start......{color.RED}end{color.NORMAL}\n'


def test_full_msg_with_postfix():
    ret = _full_msg(
        start='start',
        postfix='post ',
        end_msg='end',
        end_color='',
        use_color=False,
        cols=20,
    )
    # 6 dots: 20 - 5 - 5 - 3 - 1
    assert ret == 'start......post end\n'


def test_full_msg_postfix_not_colored():
    ret = _full_msg(
        start='start',
        postfix='post ',
        end_msg='end',
        end_color=color.RED,
        use_color=True,
        cols=20,
    )
    # 6 dots: 20 - 5 - 5 - 3 - 1
    assert ret == f'start......post {color.RED}end{color.NORMAL}\n'


@pytest.fixture
def repo_with_passing_hook(tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(git_path):
        yield git_path


@pytest.fixture
def repo_with_failing_hook(tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'failing_hook_repo')
    with cwd(git_path):
        yield git_path


@pytest.fixture
def aliased_repo(tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(git_path):
        with modify_config() as config:
            config['repos'][0]['hooks'].append(
                {'id': 'bash_hook', 'alias': 'foo_bash'},
            )
        stage_a_file()
        yield git_path


def stage_a_file(filename='foo.py'):
    open(filename, 'a').close()
    cmd_output('git', 'add', filename)


def _do_run(cap_out, store, repo, args, environ={}, config_file=C.CONFIG_FILE):
    with cwd(repo):  # replicates `main._adjust_args_and_chdir` behaviour
        ret = run(config_file, store, args, environ=environ)
    printed = cap_out.get_bytes()
    return ret, printed


def _test_run(
    cap_out, store, repo, opts, expected_outputs, expected_ret, stage,
    config_file=C.CONFIG_FILE,
):
    if stage:
        stage_a_file()
    args = run_opts(**opts)
    ret, printed = _do_run(cap_out, store, repo, args, config_file=config_file)

    assert ret == expected_ret, (ret, expected_ret, printed)
    for expected_output_part in expected_outputs:
        assert expected_output_part in printed


def test_run_all_hooks_failing(cap_out, store, repo_with_failing_hook):
    _test_run(
        cap_out,
        store,
        repo_with_failing_hook,
        {},
        (
            b'Failing hook',
            b'Failed',
            b'hook id: failing_hook',
            b'Fail\nfoo.py\n',
        ),
        expected_ret=1,
        stage=True,
    )


def test_arbitrary_bytes_hook(cap_out, store, tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'arbitrary_bytes_repo')
    with cwd(git_path):
        _test_run(
            cap_out, store, git_path, {}, (b'\xe2\x98\x83\xb2\n',), 1, True,
        )


def test_hook_that_modifies_but_returns_zero(cap_out, store, tempdir_factory):
    git_path = make_consuming_repo(
        tempdir_factory, 'modified_file_returns_zero_repo',
    )
    with cwd(git_path):
        stage_a_file('bar.py')
        _test_run(
            cap_out,
            store,
            git_path,
            {},
            (
                # The first should fail
                b'Failed',
                # With a modified file (default message + the hook's output)
                b'- files were modified by this hook\n\n'
                b'Modified: foo.py',
                # The next hook should pass despite the first modifying
                b'Passed',
                # The next hook should fail
                b'Failed',
                # bar.py was modified, but provides no additional output
                b'- files were modified by this hook\n',
            ),
            1,
            True,
        )


def test_types_hook_repository(cap_out, store, tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'types_repo')
    with cwd(git_path):
        stage_a_file('bar.py')
        stage_a_file('bar.notpy')
        ret, printed = _do_run(cap_out, store, git_path, run_opts())
        assert ret == 1
        assert b'bar.py' in printed
        assert b'bar.notpy' not in printed


def test_types_or_hook_repository(cap_out, store, tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'types_or_repo')
    with cwd(git_path):
        stage_a_file('bar.notpy')
        stage_a_file('bar.pxd')
        stage_a_file('bar.py')
        ret, printed = _do_run(cap_out, store, git_path, run_opts())
        assert ret == 1
        assert b'bar.notpy' not in printed
        assert b'bar.pxd' in printed
        assert b'bar.py' in printed


def test_exclude_types_hook_repository(cap_out, store, tempdir_factory):
    git_path = make_consuming_repo(tempdir_factory, 'exclude_types_repo')
    with cwd(git_path):
        with open('exe', 'w') as exe:
            exe.write('#!/usr/bin/env python3\n')
        make_executable('exe')
        cmd_output('git', 'add', 'exe')
        stage_a_file('bar.py')
        ret, printed = _do_run(cap_out, store, git_path, run_opts())
        assert ret == 1
        assert b'bar.py' in printed
        assert b'exe' not in printed


def test_global_exclude(cap_out, store, in_git_dir):
    config = {
        'exclude': r'^foo\.py$',
        'repos': [{'repo': 'meta', 'hooks': [{'id': 'identity'}]}],
    }
    write_config('.', config)
    open('foo.py', 'a').close()
    open('bar.py', 'a').close()
    cmd_output('git', 'add', '.')
    opts = run_opts(verbose=True)
    ret, printed = _do_run(cap_out, store, str(in_git_dir), opts)
    assert ret == 0
    # Does not contain foo.py since it was excluded
    assert printed.startswith(f'identity{"." * 65}Passed\n'.encode())
    assert printed.endswith(b'\n\n.pre-commit-config.yaml\nbar.py\n\n')


def test_global_files(cap_out, store, in_git_dir):
    config = {
        'files': r'^bar\.py$',
        'repos': [{'repo': 'meta', 'hooks': [{'id': 'identity'}]}],
    }
    write_config('.', config)
    open('foo.py', 'a').close()
    open('bar.py', 'a').close()
    cmd_output('git', 'add', '.')
    opts = run_opts(verbose=True)
    ret, printed = _do_run(cap_out, store, str(in_git_dir), opts)
    assert ret == 0
    # Does not contain foo.py since it was excluded
    assert printed.startswith(f'identity{"." * 65}Passed\n'.encode())
    assert printed.endswith(b'\n\nbar.py\n\n')


@pytest.mark.parametrize(
    ('t1', 't2', 'expected'),
    (
        (1.234, 2., b'\n- duration: 0.77s\n'),
        (1., 1., b'\n- duration: 0s\n'),
    ),
)
def test_verbose_duration(cap_out, store, in_git_dir, t1, t2, expected):
    write_config('.', {'repo': 'meta', 'hooks': [{'id': 'identity'}]})
    cmd_output('git', 'add', '.')
    opts = run_opts(verbose=True)
    with mock.patch.object(time, 'time', side_effect=(t1, t2)):
        ret, printed = _do_run(cap_out, store, str(in_git_dir), opts)
    assert ret == 0
    assert expected in printed


@pytest.mark.parametrize(
    ('args', 'expected_out'),
    [
        (
            {
                'show_diff_on_failure': True,
            },
            b'All changes made by hooks:',
        ),
        (
            {
                'show_diff_on_failure': True,
                'color': True,
            },
            b'All changes made by hooks:',
        ),
        (
            {
                'show_diff_on_failure': True,
                'all_files': True,
            },
            b'reproduce locally with: pre-commit run --all-files',
        ),
    ],
)
def test_show_diff_on_failure(
        args,
        expected_out,
        capfd,
        cap_out,
        store,
        tempdir_factory,
):
    git_path = make_consuming_repo(
        tempdir_factory, 'modified_file_returns_zero_repo',
    )
    with cwd(git_path):
        stage_a_file('bar.py')
        _test_run(
            cap_out, store, git_path, args,
            # we're only testing the output after running
            expected_out, 1, True,
        )
    out, _ = capfd.readouterr()
    assert 'diff --git' in out


@pytest.mark.parametrize(
    ('options', 'outputs', 'expected_ret', 'stage'),
    (
        ({}, (b'Bash hook', b'Passed'), 0, True),
        ({'verbose': True}, (b'foo.py\nHello World',), 0, True),
        ({'hook': 'bash_hook'}, (b'Bash hook', b'Passed'), 0, True),
        (
            {'hook': 'nope'},
            (b'No hook with id `nope` in stage `commit`',),
            1,
            True,
        ),
        (
            {'hook': 'nope', 'hook_stage': 'push'},
            (b'No hook with id `nope` in stage `push`',),
            1,
            True,
        ),
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
        store,
        repo_with_passing_hook,
        options,
        outputs,
        expected_ret,
        stage,
):
    _test_run(
        cap_out,
        store,
        repo_with_passing_hook,
        options,
        outputs,
        expected_ret,
        stage,
    )


def test_run_output_logfile(cap_out, store, tempdir_factory):
    expected_output = (
        b'This is STDOUT output\n',
        b'This is STDERR output\n',
    )

    git_path = make_consuming_repo(tempdir_factory, 'logfile_repo')
    with cwd(git_path):
        _test_run(
            cap_out,
            store,
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


def test_always_run(cap_out, store, repo_with_passing_hook):
    with modify_config() as config:
        config['repos'][0]['hooks'][0]['always_run'] = True
    _test_run(
        cap_out,
        store,
        repo_with_passing_hook,
        {},
        (b'Bash hook', b'Passed'),
        0,
        stage=False,
    )


def test_always_run_alt_config(cap_out, store, repo_with_passing_hook):
    repo_root = '.'
    config = read_config(repo_root)
    config['repos'][0]['hooks'][0]['always_run'] = True
    alt_config_file = 'alternate_config.yaml'
    add_config_to_repo(repo_root, config, config_file=alt_config_file)

    _test_run(
        cap_out,
        store,
        repo_with_passing_hook,
        {},
        (b'Bash hook', b'Passed'),
        0,
        stage=False,
        config_file=alt_config_file,
    )


def test_hook_verbose_enabled(cap_out, store, repo_with_passing_hook):
    with modify_config() as config:
        config['repos'][0]['hooks'][0]['always_run'] = True
        config['repos'][0]['hooks'][0]['verbose'] = True

    _test_run(
        cap_out,
        store,
        repo_with_passing_hook,
        {},
        (b'Hello World',),
        0,
        stage=False,
    )


@pytest.mark.parametrize(
    ('from_ref', 'to_ref'), (('master', ''), ('', 'master')),
)
def test_from_ref_to_ref_error_msg_error(
        cap_out, store, repo_with_passing_hook, from_ref, to_ref,
):
    args = run_opts(from_ref=from_ref, to_ref=to_ref)
    ret, printed = _do_run(cap_out, store, repo_with_passing_hook, args)
    assert ret == 1
    assert b'Specify both --from-ref and --to-ref.' in printed


def test_all_push_options_ok(cap_out, store, repo_with_passing_hook):
    args = run_opts(
        from_ref='master', to_ref='master',
        remote_branch='master',
        local_branch='master',
        remote_name='origin', remote_url='https://example.com/repo',
    )
    ret, printed = _do_run(cap_out, store, repo_with_passing_hook, args)
    assert ret == 0
    assert b'Specify both --from-ref and --to-ref.' not in printed


def test_is_squash_merge(cap_out, store, repo_with_passing_hook):
    args = run_opts(is_squash_merge='1')
    environ: MutableMapping[str, str] = {}
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, args, environ,
    )
    assert environ['PRE_COMMIT_IS_SQUASH_MERGE'] == '1'


def test_rewrite_command(cap_out, store, repo_with_passing_hook):
    args = run_opts(rewrite_command='amend')
    environ: MutableMapping[str, str] = {}
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, args, environ,
    )
    assert environ['PRE_COMMIT_REWRITE_COMMAND'] == 'amend'


def test_checkout_type(cap_out, store, repo_with_passing_hook):
    args = run_opts(from_ref='', to_ref='', checkout_type='1')
    environ: MutableMapping[str, str] = {}
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, args, environ,
    )
    assert environ['PRE_COMMIT_CHECKOUT_TYPE'] == '1'


def test_has_unmerged_paths(in_merge_conflict):
    assert _has_unmerged_paths() is True
    cmd_output('git', 'add', '.')
    assert _has_unmerged_paths() is False


def test_merge_conflict(cap_out, store, in_merge_conflict):
    ret, printed = _do_run(cap_out, store, in_merge_conflict, run_opts())
    assert ret == 1
    assert b'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_modified(cap_out, store, in_merge_conflict):
    # Touch another file so we have unstaged non-conflicting things
    assert os.path.exists('placeholder')
    with open('placeholder', 'w') as placeholder_file:
        placeholder_file.write('bar\nbaz\n')

    ret, printed = _do_run(cap_out, store, in_merge_conflict, run_opts())
    assert ret == 1
    assert b'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_resolved(cap_out, store, in_merge_conflict):
    cmd_output('git', 'add', '.')
    ret, printed = _do_run(cap_out, store, in_merge_conflict, run_opts())
    for msg in (
            b'Checking merge-conflict files only.', b'Bash hook', b'Passed',
    ):
        assert msg in printed


@pytest.mark.parametrize(
    ('hooks', 'expected'),
    (
        ([], 80),
        ([auto_namedtuple(id='a', name='a' * 51)], 81),
        (
            [
                auto_namedtuple(id='a', name='a' * 51),
                auto_namedtuple(id='b', name='b' * 52),
            ],
            82,
        ),
    ),
)
def test_compute_cols(hooks, expected):
    assert _compute_cols(hooks) == expected


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


def test_skip_hook(cap_out, store, repo_with_passing_hook):
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, run_opts(),
        {'SKIP': 'bash_hook'},
    )
    for msg in (b'Bash hook', b'Skipped'):
        assert msg in printed


def test_skip_aliased_hook(cap_out, store, aliased_repo):
    ret, printed = _do_run(
        cap_out, store, aliased_repo,
        run_opts(hook='foo_bash'),
        {'SKIP': 'foo_bash'},
    )
    assert ret == 0
    # Only the aliased hook runs and is skipped
    for msg in (b'Bash hook', b'Skipped'):
        assert printed.count(msg) == 1


def test_skip_bypasses_installation(cap_out, store, repo_with_passing_hook):
    config = {
        'repo': 'local',
        'hooks': [
            {
                'id': 'skipme',
                'name': 'skipme',
                'entry': 'skipme',
                'language': 'python',
                'additional_dependencies': ['/pre-commit-does-not-exist'],
            },
        ],
    }
    add_config_to_repo(repo_with_passing_hook, config)

    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook,
        run_opts(all_files=True),
        {'SKIP': 'skipme'},
    )
    assert ret == 0


def test_hook_id_not_in_non_verbose_output(
        cap_out, store, repo_with_passing_hook,
):
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, run_opts(verbose=False),
    )
    assert b'[bash_hook]' not in printed


def test_hook_id_in_verbose_output(cap_out, store, repo_with_passing_hook):
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, run_opts(verbose=True),
    )
    assert b'- hook id: bash_hook' in printed


def test_multiple_hooks_same_id(cap_out, store, repo_with_passing_hook):
    with cwd(repo_with_passing_hook):
        # Add bash hook on there again
        with modify_config() as config:
            config['repos'][0]['hooks'].append({'id': 'bash_hook'})
        stage_a_file()

    ret, output = _do_run(cap_out, store, repo_with_passing_hook, run_opts())
    assert ret == 0
    assert output.count(b'Bash hook') == 2


def test_aliased_hook_run(cap_out, store, aliased_repo):
    ret, output = _do_run(
        cap_out, store, aliased_repo,
        run_opts(verbose=True, hook='bash_hook'),
    )
    assert ret == 0
    # Both hooks will run since they share the same ID
    assert output.count(b'Bash hook') == 2

    ret, output = _do_run(
        cap_out, store, aliased_repo,
        run_opts(verbose=True, hook='foo_bash'),
    )
    assert ret == 0
    # Only the aliased hook runs
    assert output.count(b'Bash hook') == 1


def test_non_ascii_hook_id(repo_with_passing_hook, tempdir_factory):
    with cwd(repo_with_passing_hook):
        _, stdout, _ = cmd_output_mocked_pre_commit_home(
            sys.executable, '-m', 'pre_commit.main', 'run', '☃',
            retcode=None, tempdir_factory=tempdir_factory,
        )
        assert 'UnicodeDecodeError' not in stdout
        # Doesn't actually happen, but a reasonable assertion
        assert 'UnicodeEncodeError' not in stdout


def test_stdout_write_bug_py26(repo_with_failing_hook, store, tempdir_factory):
    with cwd(repo_with_failing_hook):
        with modify_config() as config:
            config['repos'][0]['hooks'][0]['args'] = ['☃']
        stage_a_file()

        install(C.CONFIG_FILE, store, hook_types=['pre-commit'])

        # Have to use subprocess because pytest monkeypatches sys.stdout
        _, out = git_commit(
            fn=cmd_output_mocked_pre_commit_home,
            tempdir_factory=tempdir_factory,
            retcode=None,
        )
        assert 'UnicodeEncodeError' not in out
        # Doesn't actually happen, but a reasonable assertion
        assert 'UnicodeDecodeError' not in out


def test_lots_of_files(store, tempdir_factory):
    # windows xargs seems to have a bug, here's a regression test for
    # our workaround
    git_path = make_consuming_repo(tempdir_factory, 'script_hooks_repo')
    with cwd(git_path):
        # Override files so we run against them
        with modify_config() as config:
            config['repos'][0]['hooks'][0]['files'] = ''

        # Write a crap ton of files
        for i in range(400):
            open(f'{"a" * 100}{i}', 'w').close()

        cmd_output('git', 'add', '.')
        install(C.CONFIG_FILE, store, hook_types=['pre-commit'])

        git_commit(
            fn=cmd_output_mocked_pre_commit_home,
            tempdir_factory=tempdir_factory,
        )


def test_stages(cap_out, store, repo_with_passing_hook):
    config = {
        'repo': 'local',
        'hooks': [
            {
                'id': f'do-not-commit-{i}',
                'name': f'hook {i}',
                'entry': 'DO NOT COMMIT',
                'language': 'pygrep',
                'stages': [stage],
            }
            for i, stage in enumerate(('commit', 'push', 'manual'), 1)
        ],
    }
    add_config_to_repo(repo_with_passing_hook, config)

    stage_a_file()

    def _run_for_stage(stage):
        args = run_opts(hook_stage=stage)
        ret, printed = _do_run(cap_out, store, repo_with_passing_hook, args)
        assert not ret, (ret, printed)
        # this test should only run one hook
        assert printed.count(b'hook ') == 1
        return printed

    assert _run_for_stage('commit').startswith(b'hook 1...')
    assert _run_for_stage('push').startswith(b'hook 2...')
    assert _run_for_stage('manual').startswith(b'hook 3...')


def test_commit_msg_hook(cap_out, store, commit_msg_repo):
    filename = '.git/COMMIT_EDITMSG'
    with open(filename, 'w') as f:
        f.write('This is the commit message')

    _test_run(
        cap_out,
        store,
        commit_msg_repo,
        {'hook_stage': 'commit-msg', 'commit_msg_filename': filename},
        expected_outputs=[b'Must have "Signed off by:"', b'Failed'],
        expected_ret=1,
        stage=False,
    )


def test_post_checkout_hook(cap_out, store, tempdir_factory):
    path = git_dir(tempdir_factory)
    config = {
        'repo': 'meta', 'hooks': [
            {'id': 'identity', 'stages': ['post-checkout']},
        ],
    }
    add_config_to_repo(path, config)

    with cwd(path):
        _test_run(
            cap_out,
            store,
            path,
            {'hook_stage': 'post-checkout'},
            expected_outputs=[b'identity...'],
            expected_ret=0,
            stage=False,
        )


def test_prepare_commit_msg_hook(cap_out, store, prepare_commit_msg_repo):
    filename = '.git/COMMIT_EDITMSG'
    with open(filename, 'w') as f:
        f.write('This is the commit message')

    _test_run(
        cap_out,
        store,
        prepare_commit_msg_repo,
        {'hook_stage': 'prepare-commit-msg', 'commit_msg_filename': filename},
        expected_outputs=[b'Add "Signed off by:"', b'Passed'],
        expected_ret=0,
        stage=False,
    )

    with open(filename) as f:
        assert 'Signed off by: ' in f.read()


def test_local_hook_passes(cap_out, store, repo_with_passing_hook):
    config = {
        'repo': 'local',
        'hooks': [
            {
                'id': 'identity-copy',
                'name': 'identity-copy',
                'entry': '{} -m pre_commit.meta_hooks.identity'.format(
                    shlex.quote(sys.executable),
                ),
                'language': 'system',
                'files': r'\.py$',
            },
            {
                'id': 'do_not_commit',
                'name': 'Block if "DO NOT COMMIT" is found',
                'entry': 'DO NOT COMMIT',
                'language': 'pygrep',
            },
        ],
    }
    add_config_to_repo(repo_with_passing_hook, config)

    with open('placeholder.py', 'w') as staged_file:
        staged_file.write('"""TODO: something"""\n')
    cmd_output('git', 'add', 'placeholder.py')

    _test_run(
        cap_out,
        store,
        repo_with_passing_hook,
        opts={},
        expected_outputs=[b''],
        expected_ret=0,
        stage=False,
    )


def test_local_hook_fails(cap_out, store, repo_with_passing_hook):
    config = {
        'repo': 'local',
        'hooks': [{
            'id': 'no-todo',
            'name': 'No TODO',
            'entry': 'sh -c "! grep -iI todo $@" --',
            'language': 'system',
        }],
    }
    add_config_to_repo(repo_with_passing_hook, config)

    with open('placeholder.py', 'w') as staged_file:
        staged_file.write('"""TODO: something"""\n')
    cmd_output('git', 'add', 'placeholder.py')

    _test_run(
        cap_out,
        store,
        repo_with_passing_hook,
        opts={},
        expected_outputs=[b''],
        expected_ret=1,
        stage=False,
    )


def test_meta_hook_passes(cap_out, store, repo_with_passing_hook):
    add_config_to_repo(repo_with_passing_hook, sample_meta_config())

    _test_run(
        cap_out,
        store,
        repo_with_passing_hook,
        opts={},
        expected_outputs=[b'Check for useless excludes'],
        expected_ret=0,
        stage=False,
    )


@pytest.fixture
def modified_config_repo(repo_with_passing_hook):
    with modify_config(repo_with_passing_hook, commit=False) as config:
        # Some minor modification
        config['repos'][0]['hooks'][0]['files'] = ''
    yield repo_with_passing_hook


def test_error_with_unstaged_config(cap_out, store, modified_config_repo):
    args = run_opts()
    ret, printed = _do_run(cap_out, store, modified_config_repo, args)
    assert b'Your pre-commit configuration is unstaged.' in printed
    assert ret == 1


def test_commit_msg_missing_filename(cap_out, store, repo_with_passing_hook):
    args = run_opts(hook_stage='commit-msg')
    ret, printed = _do_run(cap_out, store, repo_with_passing_hook, args)
    assert ret == 1
    assert printed == (
        b'[ERROR] `--commit-msg-filename` is required for '
        b'`--hook-stage commit-msg`\n'
    )


@pytest.mark.parametrize(
    'opts', (run_opts(all_files=True), run_opts(files=[C.CONFIG_FILE])),
)
def test_no_unstaged_error_with_all_files_or_files(
        cap_out, store, modified_config_repo, opts,
):
    ret, printed = _do_run(cap_out, store, modified_config_repo, opts)
    assert b'Your pre-commit configuration is unstaged.' not in printed


def test_files_running_subdir(repo_with_passing_hook, tempdir_factory):
    with cwd(repo_with_passing_hook):
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
        assert 'subdir/foo.py' in stdout


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
        cap_out, store, repo_with_passing_hook,
        pass_filenames, hook_args, expected_out,
):
    with modify_config() as config:
        config['repos'][0]['hooks'][0]['pass_filenames'] = pass_filenames
        config['repos'][0]['hooks'][0]['args'] = hook_args
    stage_a_file()
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, run_opts(verbose=True),
    )
    assert expected_out + b'\nHello World' in printed
    assert (b'foo.py' in printed) == pass_filenames


def test_fail_fast(cap_out, store, repo_with_failing_hook):
    with modify_config() as config:
        # More than one hook
        config['fail_fast'] = True
        config['repos'][0]['hooks'] *= 2
    stage_a_file()

    ret, printed = _do_run(cap_out, store, repo_with_failing_hook, run_opts())
    # it should have only run one hook
    assert printed.count(b'Failing hook') == 1


def test_classifier_removes_dne():
    classifier = Classifier(('this_file_does_not_exist',))
    assert classifier.filenames == []


def test_classifier_normalizes_filenames_on_windows_to_forward_slashes(tmpdir):
    with tmpdir.as_cwd():
        tmpdir.join('a/b/c').ensure()
        with mock.patch.object(os, 'altsep', '/'):
            with mock.patch.object(os, 'sep', '\\'):
                classifier = Classifier.from_config((r'a\b\c',), '', '^$')
                assert classifier.filenames == ['a/b/c']


def test_classifier_does_not_normalize_backslashes_non_windows(tmpdir):
    with mock.patch.object(os.path, 'lexists', return_value=True):
        with mock.patch.object(os, 'altsep', None):
            with mock.patch.object(os, 'sep', '/'):
                classifier = Classifier.from_config((r'a/b\c',), '', '^$')
                assert classifier.filenames == [r'a/b\c']


def test_classifier_empty_types_or(tmpdir):
    tmpdir.join('bar').ensure()
    os.symlink(tmpdir.join('bar'), tmpdir.join('foo'))
    with tmpdir.as_cwd():
        classifier = Classifier(('foo', 'bar'))
        for_symlink = classifier.by_types(
            classifier.filenames,
            types=['symlink'],
            types_or=[],
            exclude_types=[],
        )
        for_file = classifier.by_types(
            classifier.filenames,
            types=['file'],
            types_or=[],
            exclude_types=[],
        )
        assert for_symlink == ['foo']
        assert for_file == ['bar']


@pytest.fixture
def some_filenames():
    return (
        '.pre-commit-hooks.yaml',
        'pre_commit/git.py',
        'pre_commit/main.py',
    )


def test_include_exclude_base_case(some_filenames):
    ret = filter_by_include_exclude(some_filenames, '', '^$')
    assert ret == [
        '.pre-commit-hooks.yaml',
        'pre_commit/git.py',
        'pre_commit/main.py',
    ]


def test_matches_broken_symlink(tmpdir):
    with tmpdir.as_cwd():
        os.symlink('does-not-exist', 'link')
        ret = filter_by_include_exclude({'link'}, '', '^$')
        assert ret == ['link']


def test_include_exclude_total_match(some_filenames):
    ret = filter_by_include_exclude(some_filenames, r'^.*\.py$', '^$')
    assert ret == ['pre_commit/git.py', 'pre_commit/main.py']


def test_include_exclude_does_search_instead_of_match(some_filenames):
    ret = filter_by_include_exclude(some_filenames, r'\.yaml$', '^$')
    assert ret == ['.pre-commit-hooks.yaml']


def test_include_exclude_exclude_removes_files(some_filenames):
    ret = filter_by_include_exclude(some_filenames, '', r'\.py$')
    assert ret == ['.pre-commit-hooks.yaml']


def test_args_hook_only(cap_out, store, repo_with_passing_hook):
    config = {
        'repo': 'local',
        'hooks': [
            {
                'id': 'identity-copy',
                'name': 'identity-copy',
                'entry': '{} -m pre_commit.meta_hooks.identity'.format(
                    shlex.quote(sys.executable),
                ),
                'language': 'system',
                'files': r'\.py$',
                'stages': ['commit'],
            },
            {
                'id': 'do_not_commit',
                'name': 'Block if "DO NOT COMMIT" is found',
                'entry': 'DO NOT COMMIT',
                'language': 'pygrep',
            },
        ],
    }
    add_config_to_repo(repo_with_passing_hook, config)
    stage_a_file()
    ret, printed = _do_run(
        cap_out,
        store,
        repo_with_passing_hook,
        run_opts(hook='do_not_commit'),
    )
    assert b'identity-copy' not in printed


def test_skipped_without_any_setup_for_post_checkout(in_git_dir, store):
    environ = {'_PRE_COMMIT_SKIP_POST_CHECKOUT': '1'}
    opts = run_opts(hook_stage='post-checkout')
    assert run(C.CONFIG_FILE, store, opts, environ=environ) == 0


def test_pre_commit_env_variable_set(cap_out, store, repo_with_passing_hook):
    args = run_opts()
    environ: MutableMapping[str, str] = {}
    ret, printed = _do_run(
        cap_out, store, repo_with_passing_hook, args, environ,
    )
    assert environ['PRE_COMMIT'] == '1'
