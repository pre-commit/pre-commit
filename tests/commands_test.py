import mock
import os
import os.path
import pkg_resources
import pytest
import shutil
import stat
from asottile.ordereddict import OrderedDict
from asottile.yaml import ordered_dump
from plumbum import local

import pre_commit.constants as C
from pre_commit import commands
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.runner import Runner
from testing.auto_namedtuple import auto_namedtuple
from testing.util import get_head_sha
from testing.util import get_resource_path


@pytest.yield_fixture
def runner_with_mocked_store(mock_out_store_directory):
    yield Runner('/')


def test_install_pre_commit(empty_git_dir):
    runner = Runner(empty_git_dir)
    ret = commands.install(runner)
    assert ret == 0
    assert os.path.exists(runner.pre_commit_path)
    pre_commit_contents = open(runner.pre_commit_path).read()
    pre_commit_sh = pkg_resources.resource_filename('pre_commit', 'resources/pre-commit.sh')
    expected_contents = open(pre_commit_sh).read()
    assert pre_commit_contents == expected_contents
    stat_result = os.stat(runner.pre_commit_path)
    assert stat_result.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_uninstall_pre_commit_does_not_blow_up_when_not_there(empty_git_dir):
    runner = Runner(empty_git_dir)
    ret = commands.uninstall(runner)
    assert ret == 0


def test_uninstall(empty_git_dir):
    runner = Runner(empty_git_dir)
    assert not os.path.exists(runner.pre_commit_path)
    commands.install(runner)
    assert os.path.exists(runner.pre_commit_path)
    commands.uninstall(runner)
    assert not os.path.exists(runner.pre_commit_path)


@pytest.yield_fixture
def up_to_date_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', get_head_sha(python_hooks_repo)),
        ('hooks', [OrderedDict((('id', 'foo'), ('files', '')))]),
    ))
    wrapped_config = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(wrapped_config)
    config = wrapped_config[0]

    with open(os.path.join(python_hooks_repo, C.CONFIG_FILE), 'w') as file_obj:
        file_obj.write(
            ordered_dump([config], **C.YAML_DUMP_KWARGS)
        )

    yield auto_namedtuple(
        repo_config=config,
        python_hooks_repo=python_hooks_repo,
    )


def test_up_to_date_repo(up_to_date_repo, runner_with_mocked_store):
    input_sha = up_to_date_repo.repo_config['sha']
    ret = commands._update_repository(
        up_to_date_repo.repo_config, runner_with_mocked_store,
    )
    assert ret['sha'] == input_sha


def test_autoupdate_up_to_date_repo(up_to_date_repo, mock_out_store_directory):
    before = open(C.CONFIG_FILE).read()
    runner = Runner(up_to_date_repo.python_hooks_repo)
    ret = commands.autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before == after


@pytest.yield_fixture
def out_of_date_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', get_head_sha(python_hooks_repo)),
        ('hooks', [OrderedDict((('id', 'foo'), ('files', '')))]),
    ))
    config_wrapped = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(config_wrapped)
    config = config_wrapped[0]
    local['git']['commit', '--allow-empty', '-m', 'foo']()
    head_sha = get_head_sha(python_hooks_repo)

    with open(os.path.join(python_hooks_repo, C.CONFIG_FILE), 'w') as file_obj:
        file_obj.write(
            ordered_dump([config], **C.YAML_DUMP_KWARGS)
        )

    yield auto_namedtuple(
        repo_config=config,
        head_sha=head_sha,
        python_hooks_repo=python_hooks_repo,
    )


def test_out_of_date_repo(out_of_date_repo, runner_with_mocked_store):
    ret = commands._update_repository(
        out_of_date_repo.repo_config, runner_with_mocked_store,
    )
    assert ret['sha'] == out_of_date_repo.head_sha


def test_removes_defaults(out_of_date_repo, runner_with_mocked_store):
    ret = commands._update_repository(
        out_of_date_repo.repo_config, runner_with_mocked_store,
    )
    assert 'args' not in ret['hooks'][0]
    assert 'expected_return_value' not in ret['hooks'][0]


def test_autoupdate_out_of_date_repo(out_of_date_repo, mock_out_store_directory):
    before = open(C.CONFIG_FILE).read()
    runner = Runner(out_of_date_repo.python_hooks_repo)
    ret = commands.autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before != after
    assert out_of_date_repo.head_sha in after


@pytest.yield_fixture
def hook_disappearing_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', get_head_sha(python_hooks_repo)),
        ('hooks', [OrderedDict((('id', 'foo'), ('files', '')))]),
    ))
    config_wrapped = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(config_wrapped)
    config = config_wrapped[0]
    shutil.copy(get_resource_path('manifest_without_foo.yaml'), C.MANIFEST_FILE)
    local['git']['add', '.']()
    local['git']['commit', '-m', 'Remove foo']()

    with open(os.path.join(python_hooks_repo, C.CONFIG_FILE), 'w') as file_obj:
        file_obj.write(
            ordered_dump([config], **C.YAML_DUMP_KWARGS)
        )

    yield auto_namedtuple(
        repo_config=config,
        python_hooks_repo=python_hooks_repo,
    )


def test_hook_disppearing_repo_raises(hook_disappearing_repo, runner_with_mocked_store):
    with pytest.raises(commands.RepositoryCannotBeUpdatedError):
        commands._update_repository(
            hook_disappearing_repo.repo_config, runner_with_mocked_store,
        )


def test_autoupdate_hook_disappearing_repo(hook_disappearing_repo, mock_out_store_directory):
    before = open(C.CONFIG_FILE).read()
    runner = Runner(hook_disappearing_repo.python_hooks_repo)
    ret = commands.autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 1
    assert before == after


def test_clean(runner_with_mocked_store):
    assert os.path.exists(runner_with_mocked_store.store.directory)
    commands.clean(runner_with_mocked_store)
    assert not os.path.exists(runner_with_mocked_store.store.directory)


def test_clean_empty(runner_with_mocked_store):
    """Make sure clean succeeds when we the directory doesn't exist."""
    shutil.rmtree(runner_with_mocked_store.store.directory)
    assert not os.path.exists(runner_with_mocked_store.store.directory)
    commands.clean(runner_with_mocked_store)
    assert not os.path.exists(runner_with_mocked_store.store.directory)


def stage_a_file():
    local['touch']['foo.py']()
    local['git']['add', 'foo.py']()


def get_write_mock_output(write_mock):
    return ''.join(call[0][0] for call in write_mock.call_args_list)


def _get_opts(all_files=False, color=False, verbose=False, hook=None, no_stash=False):
    return auto_namedtuple(
        all_files=all_files,
        color=color,
        verbose=verbose,
        hook=hook,
        no_stash=no_stash,
    )


def _do_run(repo, args, environ={}):
    runner = Runner(repo)
    write_mock = mock.Mock()
    ret = commands.run(runner, args, write=write_mock, environ=environ)
    printed = get_write_mock_output(write_mock)
    return ret, printed


def _test_run(repo, options, expected_outputs, expected_ret, stage):
    if stage:
        stage_a_file()
    args = _get_opts(**options)
    ret, printed = _do_run(repo, args)
    assert ret == expected_ret
    for expected_output_part in expected_outputs:
        assert expected_output_part in printed


def test_run_all_hooks_failing(repo_with_failing_hook, mock_out_store_directory):
    _test_run(
        repo_with_failing_hook,
        {},
        ('Failing hook', 'Failed', 'Fail\nfoo.py\n'),
        1,
        True,
    )


@pytest.mark.parametrize(
    ('options', 'outputs', 'expected_ret', 'stage'),
    (
        ({}, ('Bash hook', 'Passed'), 0, True),
        ({'verbose': True}, ('foo.py\nHello World',), 0, True),
        ({'hook': 'bash_hook'}, ('Bash hook', 'Passed'), 0, True),
        ({'hook': 'nope'}, ('No hook with id `nope`',), 1, True),
        # All the files in the repo.
        # This seems kind of weird but it is beacuse py.test reuses fixtures
        (
            {'all_files': True, 'verbose': True},
            ('hooks.yaml', 'bin/hook.sh', 'foo.py', 'dummy'),
            0,
            True,
        ),
        ({}, ('Bash hook', '(no files to check)', 'Skipped'), 0, False),
    )
)
def test_run(repo_with_passing_hook, options, outputs, expected_ret, stage, mock_out_store_directory):
    _test_run(repo_with_passing_hook, options, outputs, expected_ret, stage)


@pytest.mark.parametrize(
    ('no_stash', 'all_files', 'expect_stash'),
    (
        (True, True, False),
        (True, False, False),
        (False, True, False),
        (False, False, True),
    ),
)
def test_no_stash(repo_with_passing_hook, no_stash, all_files, expect_stash, mock_out_store_directory):
    stage_a_file()
    # Make unstaged changes
    with open('foo.py', 'w') as foo_file:
        foo_file.write('import os\n')

    args = _get_opts(no_stash=no_stash, all_files=all_files)
    ret, printed = _do_run(repo_with_passing_hook, args)
    assert ret == 0
    warning_msg = '[WARNING] Unstaged files detected.'
    if expect_stash:
        assert warning_msg in printed
    else:
        assert warning_msg not in printed


@pytest.mark.parametrize(('output', 'expected'), (('some', True), ('', False)))
def test_has_unmerged_paths(output, expected):
    mock_runner = mock.Mock()
    mock_runner.cmd_runner.run.return_value = (1, output, '')
    assert commands._has_unmerged_paths(mock_runner) is expected


def test_merge_conflict(in_merge_conflict, mock_out_store_directory):
    ret, printed = _do_run(in_merge_conflict, _get_opts())
    assert ret == 1
    assert 'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_modified(in_merge_conflict, mock_out_store_directory):
    # Touch another file so we have unstaged non-conflicting things
    assert os.path.exists('dummy')
    with open('dummy', 'w') as dummy_file:
        dummy_file.write('bar\nbaz\n')

    ret, printed = _do_run(in_merge_conflict, _get_opts())
    assert ret == 1
    assert 'Unmerged files.  Resolve before committing.' in printed


def test_merge_conflict_resolved(in_merge_conflict, mock_out_store_directory):
    local['git']['add', '.']()
    ret, printed = _do_run(in_merge_conflict, _get_opts())
    for msg in ('Checking merge-conflict files only.', 'Bash hook', 'Passed'):
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
    ret = commands._get_skips(environ)
    assert ret == expected_output


def test_skip_hook(repo_with_passing_hook, mock_out_store_directory):
    ret, printed = _do_run(
        repo_with_passing_hook, _get_opts(), {'SKIP': 'bash_hook'},
    )
    for msg in ('Bash hook', 'Skipped'):
        assert msg in printed


def test_hook_id_not_in_non_verbose_output(repo_with_passing_hook, mock_out_store_directory):
    ret, printed = _do_run(repo_with_passing_hook, _get_opts(verbose=False))
    assert '[bash_hook]' not in printed


def test_hook_id_in_verbose_output(repo_with_passing_hook, mock_out_store_directory):
    ret, printed = _do_run(repo_with_passing_hook, _get_opts(verbose=True))
    assert '[bash_hook] Bash hook' in printed
