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
from pre_commit import git
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.runner import Runner
from testing.auto_namedtuple import auto_namedtuple
from testing.util import get_resource_path


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
        ('sha', git.get_head_sha(python_hooks_repo)),
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


def test_up_to_date_repo(up_to_date_repo):
    input_sha = up_to_date_repo.repo_config['sha']
    ret = commands._update_repository(up_to_date_repo.repo_config)
    assert ret['sha'] == input_sha


def test_autoupdate_up_to_date_repo(up_to_date_repo):
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
        ('sha', git.get_head_sha(python_hooks_repo)),
        ('hooks', [OrderedDict((('id', 'foo'), ('files', '')))]),
    ))
    config_wrapped = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(config_wrapped)
    config = config_wrapped[0]
    local['git']['commit', '--allow-empty', '-m', 'foo']()
    head_sha = git.get_head_sha(python_hooks_repo)

    with open(os.path.join(python_hooks_repo, C.CONFIG_FILE), 'w') as file_obj:
        file_obj.write(
            ordered_dump([config], **C.YAML_DUMP_KWARGS)
        )

    yield auto_namedtuple(
        repo_config=config,
        head_sha=head_sha,
        python_hooks_repo=python_hooks_repo,
    )


def test_out_of_date_repo(out_of_date_repo):
    ret = commands._update_repository(out_of_date_repo.repo_config)
    assert ret['sha'] == out_of_date_repo.head_sha


def test_removes_defaults(out_of_date_repo):
    ret = commands._update_repository(out_of_date_repo.repo_config)
    assert 'args' not in ret['hooks'][0]
    assert 'expected_return_value' not in ret['hooks'][0]


def test_autoupdate_out_of_date_repo(out_of_date_repo):
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
        ('sha', git.get_head_sha(python_hooks_repo)),
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


def test_hook_disppearing_repo_raises(hook_disappearing_repo):
    with pytest.raises(commands.RepositoryCannotBeUpdatedError):
        commands._update_repository(hook_disappearing_repo.repo_config)


def test_autoupdate_hook_disappearing_repo(hook_disappearing_repo):
    before = open(C.CONFIG_FILE).read()
    runner = Runner(hook_disappearing_repo.python_hooks_repo)
    ret = commands.autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 1
    assert before == after


def test_clean(empty_git_dir):
    os.mkdir(C.HOOKS_WORKSPACE)
    commands.clean(Runner(empty_git_dir))
    assert not os.path.exists(C.HOOKS_WORKSPACE)


def test_clean_empty(empty_git_dir):
    assert not os.path.exists(C.HOOKS_WORKSPACE)
    commands.clean(Runner(empty_git_dir))
    assert not os.path.exists(C.HOOKS_WORKSPACE)


def stage_a_file():
    local['touch']['foo.py']()
    local['git']['add', 'foo.py']()


def get_write_mock_output(write_mock):
    return ''.join(call[0][0] for call in write_mock.call_args_list)


def _test_run(repo, options, expected_outputs, expected_ret, stage):
    if stage:
        stage_a_file()
    runner = Runner(repo)
    args = auto_namedtuple(
        **dict(
            dict(all_files=False, color=False, verbose=False, hook=None),
            **options
        )
    )
    write_mock = mock.Mock()
    ret = commands.run(runner, args, write=write_mock)
    assert ret == expected_ret
    printed = get_write_mock_output(write_mock)
    for expected_output_part in expected_outputs:
        assert expected_output_part in printed


def test_run_all_hooks_failing(repo_with_failing_hook):
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
def test_run(repo_with_passing_hook, options, outputs, expected_ret, stage):
    _test_run(repo_with_passing_hook, options, outputs, expected_ret, stage)
