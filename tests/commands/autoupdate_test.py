from __future__ import unicode_literals

import shutil

import pytest

import pre_commit.constants as C
from pre_commit.commands.autoupdate import _update_repository
from pre_commit.commands.autoupdate import autoupdate
from pre_commit.commands.autoupdate import RepositoryCannotBeUpdatedError
from pre_commit.ordereddict import OrderedDict
from pre_commit.runner import Runner
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.auto_namedtuple import auto_namedtuple
from testing.fixtures import add_config_to_repo
from testing.fixtures import config_with_local_hooks
from testing.fixtures import git_dir
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.fixtures import write_config
from testing.util import get_head_sha
from testing.util import get_resource_path


@pytest.yield_fixture
def up_to_date_repo(tmpdir_factory):
    yield make_repo(tmpdir_factory, 'python_hooks_repo')


def test_up_to_date_repo(up_to_date_repo, runner_with_mocked_store):
    config = make_config_from_repo(up_to_date_repo)
    input_sha = config['sha']
    ret = _update_repository(config, runner_with_mocked_store)
    assert ret['sha'] == input_sha


def test_autoupdate_up_to_date_repo(
        up_to_date_repo, in_tmpdir, mock_out_store_directory,
):
    # Write out the config
    config = make_config_from_repo(up_to_date_repo, check=False)
    write_config('.', config)

    before = open(C.CONFIG_FILE).read()
    assert '^$' not in before
    runner = Runner('.')
    ret = autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before == after


@pytest.yield_fixture
def out_of_date_repo(tmpdir_factory):
    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    original_sha = get_head_sha(path)

    # Make a commit
    with cwd(path):
        cmd_output('git', 'commit', '--allow-empty', '-m', 'foo')
    head_sha = get_head_sha(path)

    yield auto_namedtuple(
        path=path, original_sha=original_sha, head_sha=head_sha,
    )


def test_out_of_date_repo(out_of_date_repo, runner_with_mocked_store):
    config = make_config_from_repo(
        out_of_date_repo.path, sha=out_of_date_repo.original_sha,
    )
    ret = _update_repository(config, runner_with_mocked_store)
    assert ret['sha'] != out_of_date_repo.original_sha
    assert ret['sha'] == out_of_date_repo.head_sha


def test_autoupdate_out_of_date_repo(
        out_of_date_repo, in_tmpdir, mock_out_store_directory
):
    # Write out the config
    config = make_config_from_repo(
        out_of_date_repo.path, sha=out_of_date_repo.original_sha, check=False,
    )
    write_config('.', config)

    before = open(C.CONFIG_FILE).read()
    runner = Runner('.')
    ret = autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before != after
    # Make sure we don't add defaults
    assert 'exclude' not in after
    assert out_of_date_repo.head_sha in after


@pytest.yield_fixture
def hook_disappearing_repo(tmpdir_factory):
    path = make_repo(tmpdir_factory, 'python_hooks_repo')
    original_sha = get_head_sha(path)

    with cwd(path):
        shutil.copy(
            get_resource_path('manifest_without_foo.yaml'),
            C.MANIFEST_FILE,
        )
        cmd_output('git', 'add', '.')
        cmd_output('git', 'commit', '-m', 'Remove foo')

    yield auto_namedtuple(path=path, original_sha=original_sha)


def test_hook_disppearing_repo_raises(
        hook_disappearing_repo, runner_with_mocked_store
):
    config = make_config_from_repo(
        hook_disappearing_repo.path,
        sha=hook_disappearing_repo.original_sha,
        hooks=[OrderedDict((('id', 'foo'),))],
    )
    with pytest.raises(RepositoryCannotBeUpdatedError):
        _update_repository(config, runner_with_mocked_store)


def test_autoupdate_hook_disappearing_repo(
        hook_disappearing_repo, in_tmpdir, mock_out_store_directory
):
    config = make_config_from_repo(
        hook_disappearing_repo.path,
        sha=hook_disappearing_repo.original_sha,
        hooks=[OrderedDict((('id', 'foo'),))],
        check=False,
    )
    write_config('.', config)

    before = open(C.CONFIG_FILE).read()
    runner = Runner('.')
    ret = autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 1
    assert before == after


def test_autoupdate_local_hooks(tmpdir_factory):
    git_path = git_dir(tmpdir_factory)
    config = config_with_local_hooks()
    path = add_config_to_repo(git_path, config)
    assert autoupdate(Runner(path)) == 0
