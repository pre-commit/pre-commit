
import jsonschema
import os
import os.path
import pkg_resources
import pytest
import shutil
import stat
from plumbum import local

from pre_commit import git
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.commands import install
from pre_commit.commands import RepositoryCannotBeUpdatedError
from pre_commit.commands import uninstall
from pre_commit.commands import _update_repository
from pre_commit.ordereddict import OrderedDict
from pre_commit.runner import Runner
from testing.auto_namedtuple import auto_namedtuple
from testing.util import get_resource_path


def test_install_pre_commit(empty_git_dir):
    runner = Runner(empty_git_dir)
    ret = install(runner)
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
    ret = uninstall(runner)
    assert ret == 0


def test_uninstall(empty_git_dir):
    runner = Runner(empty_git_dir)
    assert not os.path.exists(runner.pre_commit_path)
    install(runner)
    assert os.path.exists(runner.pre_commit_path)
    uninstall(runner)
    assert not os.path.exists(runner.pre_commit_path)


@pytest.yield_fixture
def up_to_date_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', git.get_head_sha(python_hooks_repo)),
        ('hooks', [{'id': 'foo', 'files': ''}]),
    ))
    jsonschema.validate([config], CONFIG_JSON_SCHEMA)
    validate_config_extra([config])
    yield auto_namedtuple(
        repo_config=config,
        python_hooks_repo=python_hooks_repo,
    )


def test_up_to_date_repo(up_to_date_repo):
    input_sha = up_to_date_repo.repo_config['sha']
    ret = _update_repository(up_to_date_repo.repo_config)
    assert ret['sha'] == input_sha


@pytest.yield_fixture
def out_of_date_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', git.get_head_sha(python_hooks_repo)),
        ('hooks', [{'id': 'foo', 'files': ''}]),
    ))
    jsonschema.validate([config], CONFIG_JSON_SCHEMA)
    validate_config_extra([config])
    local['git']['commit', '--allow-empty', '-m', 'foo']()
    head_sha = git.get_head_sha(python_hooks_repo)
    yield auto_namedtuple(
        repo_config=config,
        head_sha=head_sha,
        python_hooks_repo=python_hooks_repo,
    )


def test_out_of_date_repo(out_of_date_repo):
    ret = _update_repository(out_of_date_repo.repo_config)
    assert ret['sha'] == out_of_date_repo.head_sha


@pytest.yield_fixture
def hook_disappearing_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', git.get_head_sha(python_hooks_repo)),
        ('hooks', [{'id': 'foo', 'files': ''}]),
    ))
    jsonschema.validate([config], CONFIG_JSON_SCHEMA)
    validate_config_extra([config])
    shutil.copy(get_resource_path('manifest_without_foo.yaml'), 'manifest.yaml')
    local['git']['add', '.']()
    local['git']['commit', '-m', 'Remove foo']()
    yield auto_namedtuple(
        repo_config=config,
        python_hooks_repo=python_hooks_repo,
    )


def test_hook_disppearing_repo_raises(hook_disappearing_repo):
    with pytest.raises(RepositoryCannotBeUpdatedError):
        _update_repository(hook_disappearing_repo.repo_config)
