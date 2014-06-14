from __future__ import unicode_literals

import os
import os.path
import pytest
import shutil
from asottile.ordereddict import OrderedDict
from asottile.yaml import ordered_dump
from plumbum import local

import pre_commit.constants as C
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.commands.autoupdate import _update_repository
from pre_commit.commands.autoupdate import autoupdate
from pre_commit.commands.autoupdate import RepositoryCannotBeUpdatedError
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.jsonschema_extensions import remove_defaults
from pre_commit.runner import Runner
from testing.auto_namedtuple import auto_namedtuple
from testing.util import get_head_sha
from testing.util import get_resource_path


@pytest.yield_fixture
def up_to_date_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', get_head_sha(python_hooks_repo)),
        ('hooks', [OrderedDict((('id', 'foo'),))]),
    ))
    wrapped_config = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(wrapped_config)
    config = wrapped_config[0]

    with open(os.path.join(python_hooks_repo, C.CONFIG_FILE), 'w') as file_obj:
        file_obj.write(
            ordered_dump(
                remove_defaults([config], CONFIG_JSON_SCHEMA),
                **C.YAML_DUMP_KWARGS
            )
        )

    yield auto_namedtuple(
        repo_config=config,
        python_hooks_repo=python_hooks_repo,
    )


def test_up_to_date_repo(up_to_date_repo, runner_with_mocked_store):
    input_sha = up_to_date_repo.repo_config['sha']
    ret = _update_repository(
        up_to_date_repo.repo_config, runner_with_mocked_store,
    )
    assert ret['sha'] == input_sha


def test_autoupdate_up_to_date_repo(up_to_date_repo, mock_out_store_directory):
    before = open(C.CONFIG_FILE).read()
    assert '^$' not in before
    runner = Runner(up_to_date_repo.python_hooks_repo)
    ret = autoupdate(runner)
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
    ret = _update_repository(
        out_of_date_repo.repo_config, runner_with_mocked_store,
    )
    assert ret['sha'] == out_of_date_repo.head_sha


def test_autoupdate_out_of_date_repo(
        out_of_date_repo, mock_out_store_directory
):
    before = open(C.CONFIG_FILE).read()
    runner = Runner(out_of_date_repo.python_hooks_repo)
    ret = autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 0
    assert before != after
    # Make sure we don't add defaults
    assert 'exclude' not in after
    assert out_of_date_repo.head_sha in after


@pytest.yield_fixture
def hook_disappearing_repo(python_hooks_repo):
    config = OrderedDict((
        ('repo', python_hooks_repo),
        ('sha', get_head_sha(python_hooks_repo)),
        ('hooks', [OrderedDict((('id', 'foo'),))]),
    ))
    config_wrapped = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(config_wrapped)
    config = config_wrapped[0]
    shutil.copy(
        get_resource_path('manifest_without_foo.yaml'),
        C.MANIFEST_FILE,
    )
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


def test_hook_disppearing_repo_raises(
        hook_disappearing_repo, runner_with_mocked_store
):
    with pytest.raises(RepositoryCannotBeUpdatedError):
        _update_repository(
            hook_disappearing_repo.repo_config, runner_with_mocked_store,
        )


def test_autoupdate_hook_disappearing_repo(
        hook_disappearing_repo, mock_out_store_directory
):
    before = open(C.CONFIG_FILE).read()
    runner = Runner(hook_disappearing_repo.python_hooks_repo)
    ret = autoupdate(runner)
    after = open(C.CONFIG_FILE).read()
    assert ret == 1
    assert before == after
