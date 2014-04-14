from __future__ import absolute_import

import pytest
import time
import yaml
from plumbum import local

import pre_commit.constants as C
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from testing.util import copy_tree_to_path
from testing.util import get_head_sha
from testing.util import get_resource_path


@pytest.yield_fixture
def in_tmpdir(tmpdir):
    with local.cwd(tmpdir.strpath):
        yield tmpdir.strpath


@pytest.yield_fixture
def empty_git_dir(in_tmpdir):
    local['git']['init']()
    yield in_tmpdir


def add_and_commit():
    local['git']['add', '.']()
    local['git']['commit', '-m', 'random commit {0}'.format(time.time())]()


@pytest.yield_fixture
def dummy_git_repo(empty_git_dir):
    # This is needed otherwise there is no `HEAD`
    local['touch']['dummy']()
    add_and_commit()
    yield empty_git_dir


def _make_repo(repo_path, repo_source):
    copy_tree_to_path(get_resource_path(repo_source), repo_path)
    add_and_commit()
    return repo_path


@pytest.yield_fixture
def python_hooks_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'python_hooks_repo')


@pytest.yield_fixture
def node_hooks_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'node_hooks_repo')


@pytest.yield_fixture
def consumer_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'consumer_repo')


@pytest.yield_fixture
def prints_cwd_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'prints_cwd_repo')


@pytest.yield_fixture
def script_hooks_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'script_hooks_repo')


@pytest.yield_fixture
def failing_hook_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'failing_hook_repo')


def _make_config(path, hook_id, file_regex):
    config = {
        'repo': path,
        'sha': get_head_sha(path),
        'hooks': [{'id': hook_id, 'files': file_regex}],
    }
    config_wrapped = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(config_wrapped)
    return config_wrapped[0]


@pytest.yield_fixture
def config_for_node_hooks_repo(node_hooks_repo):
    yield _make_config(node_hooks_repo, 'foo', '\\.js$')


@pytest.yield_fixture
def config_for_python_hooks_repo(python_hooks_repo):
    yield _make_config(python_hooks_repo, 'foo', '\\.py$')


@pytest.yield_fixture
def config_for_prints_cwd_repo(prints_cwd_repo):
    yield _make_config(prints_cwd_repo, 'prints_cwd', '^$')


@pytest.yield_fixture
def config_for_script_hooks_repo(script_hooks_repo):
    yield _make_config(script_hooks_repo, 'bash_hook', '')


def _make_repo_from_configs(*configs):
    with open(C.CONFIG_FILE, 'w') as config_file:
        yaml.dump(
            configs,
            stream=config_file,
            Dumper=yaml.SafeDumper,
            **C.YAML_DUMP_KWARGS
        )


@pytest.yield_fixture
def repo_with_passing_hook(config_for_script_hooks_repo, empty_git_dir):
    _make_repo_from_configs(config_for_script_hooks_repo)
    yield empty_git_dir


@pytest.yield_fixture
def repo_with_failing_hook(failing_hook_repo, empty_git_dir):
    _make_repo_from_configs(_make_config(failing_hook_repo, 'failing_hook', ''))
    yield empty_git_dir
