from __future__ import absolute_import

import mock
import os
import os.path
import pytest
import time
import yaml
from plumbum import local

import pre_commit.constants as C
from pre_commit import five
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.store import Store
from testing.util import copy_tree_to_path
from testing.util import get_head_sha
from testing.util import get_resource_path


@pytest.yield_fixture
def tmpdir_factory(tmpdir):
    class TmpdirFactory(object):
        def __init__(self):
            self.tmpdir_count = 0

        def get(self):
            path = os.path.join(tmpdir.strpath, five.text(self.tmpdir_count))
            self.tmpdir_count += 1
            os.mkdir(path)
            return path

    yield TmpdirFactory()


@pytest.yield_fixture
def in_tmpdir(tmpdir_factory):
    path = tmpdir_factory.get()
    with local.cwd(path):
        yield path


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
def python3_hooks_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'python3_hooks_repo')


@pytest.yield_fixture
def node_hooks_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'node_hooks_repo')


@pytest.yield_fixture
def node_0_11_8_hooks_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'node_0_11_8_hooks_repo')


@pytest.yield_fixture
def ruby_hooks_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'ruby_hooks_repo')


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


@pytest.yield_fixture
def system_hook_with_spaces_repo(dummy_git_repo):
    yield _make_repo(dummy_git_repo, 'system_hook_with_spaces_repo')


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
def config_for_node_0_11_8_hooks_repo(node_0_11_8_hooks_repo):
    yield _make_config(node_0_11_8_hooks_repo, 'node-11-8-hook', '\\.js$')


@pytest.yield_fixture
def config_for_ruby_hooks_repo(ruby_hooks_repo):
    yield _make_config(ruby_hooks_repo, 'ruby_hook', '\\.rb$')


@pytest.yield_fixture
def config_for_python_hooks_repo(python_hooks_repo):
    yield _make_config(python_hooks_repo, 'foo', '\\.py$')


@pytest.yield_fixture
def config_for_python3_hooks_repo(python3_hooks_repo):
    yield _make_config(python3_hooks_repo, 'python3-hook', '\\.py$')


@pytest.yield_fixture
def config_for_prints_cwd_repo(prints_cwd_repo):
    yield _make_config(prints_cwd_repo, 'prints_cwd', '^$')


@pytest.yield_fixture
def config_for_script_hooks_repo(script_hooks_repo):
    yield _make_config(script_hooks_repo, 'bash_hook', '')


@pytest.yield_fixture
def config_for_system_hook_with_spaces(system_hook_with_spaces_repo):
    yield _make_config(
        system_hook_with_spaces_repo, 'system-hook-with-spaces', '',
    )


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


@pytest.yield_fixture
def in_merge_conflict(repo_with_passing_hook):
    local['git']['add', C.CONFIG_FILE]()
    local['git']['commit', '-m' 'add hooks file']()
    local['git']['clone', '.', 'foo']()
    with local.cwd('foo'):
        local['git']['checkout', 'origin/master', '-b', 'foo']()
        with open('conflict_file', 'w') as conflict_file:
            conflict_file.write('herp\nderp\n')
        local['git']['add', 'conflict_file']()
        with open('foo_only_file', 'w') as foo_only_file:
            foo_only_file.write('foo')
        local['git']['add', 'foo_only_file']()
        local['git']['commit', '-m', 'conflict_file']()
        local['git']['checkout', 'origin/master', '-b', 'bar']()
        with open('conflict_file', 'w') as conflict_file:
            conflict_file.write('harp\nddrp\n')
        local['git']['add', 'conflict_file']()
        with open('bar_only_file', 'w') as bar_only_file:
            bar_only_file.write('bar')
        local['git']['add', 'bar_only_file']()
        local['git']['commit', '-m', 'conflict_file']()
        local['git']['merge', 'foo'](retcode=None)
        yield os.path.join(repo_with_passing_hook, 'foo')


@pytest.yield_fixture(scope='session', autouse=True)
def dont_write_to_home_directory():
    """pre_commit.store.Store will by default write to the home directory
    We'll mock out `Store.get_default_directory` to raise invariantly so we
    don't construct a `Store` object that writes to our home directory.
    """
    class YouForgotToExplicitlyChooseAStoreDirectory(AssertionError):
        pass

    with mock.patch.object(
        Store,
        'get_default_directory',
        side_effect=YouForgotToExplicitlyChooseAStoreDirectory,
    ):
        yield


@pytest.yield_fixture
def mock_out_store_directory(tmpdir_factory):
    tmpdir = tmpdir_factory.get()
    with mock.patch.object(
        Store,
        'get_default_directory',
        return_value=tmpdir,
    ):
        yield tmpdir


@pytest.yield_fixture
def store(tmpdir_factory):
    yield Store(os.path.join(tmpdir_factory.get(), '.pre-commit'))


@pytest.yield_fixture
def cmd_runner(tmpdir_factory):
    yield PrefixedCommandRunner(tmpdir_factory.get())
