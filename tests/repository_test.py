import os.path
import pytest
from plumbum import local

from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.repository import Repository


@pytest.mark.integration
def test_install_python_repo_in_env(config_for_python_hooks_repo, store):
    repo = Repository.create(config_for_python_hooks_repo, store)
    repo.install()
    assert os.path.exists(os.path.join(store.directory, repo.sha, 'py_env'))


@pytest.mark.integration
def test_run_a_python_hook(config_for_python_hooks_repo, store):
    repo = Repository.create(config_for_python_hooks_repo, store)
    ret = repo.run_hook('foo', ['/dev/null'])

    assert ret[0] == 0
    assert ret[1] == "['/dev/null']\nHello World\n"


@pytest.mark.integration
def test_lots_of_files(config_for_python_hooks_repo, store):
    repo = Repository.create(config_for_python_hooks_repo, store)
    ret = repo.run_hook('foo', ['/dev/null'] * 15000)

    assert ret[0] == 0


@pytest.mark.integration
def test_cwd_of_hook(config_for_prints_cwd_repo, store):
    # Note: this doubles as a test for `system` hooks
    repo = Repository.create(config_for_prints_cwd_repo, store)
    ret = repo.run_hook('prints_cwd', [])

    assert ret[0] == 0
    assert ret[1] == repo.repo_url + '\n'


@pytest.mark.skipif(
    os.environ.get('slowtests', None) == 'false',
    reason="TODO: make this test not super slow",
)
@pytest.mark.integration
def test_run_a_node_hook(config_for_node_hooks_repo, store):
    repo = Repository.create(config_for_node_hooks_repo, store)
    ret = repo.run_hook('foo', [])

    assert ret[0] == 0
    assert ret[1] == 'Hello World\n'


@pytest.mark.integration
def test_run_a_script_hook(config_for_script_hooks_repo, store):
    repo = Repository.create(config_for_script_hooks_repo, store)
    ret = repo.run_hook('bash_hook', ['bar'])

    assert ret[0] == 0
    assert ret[1] == 'bar\nHello World\n'


@pytest.fixture
def mock_repo_config():
    config = {
        'repo': 'git@github.com:pre-commit/pre-commit-hooks',
        'sha': '5e713f8878b7d100c0e059f8cc34be4fc2e8f897',
        'hooks': [{
            'id': 'pyflakes',
            'files': '\\.py$',
        }],
    }
    config_wrapped = apply_defaults([config], CONFIG_JSON_SCHEMA)
    validate_config_extra(config_wrapped)
    return config_wrapped[0]


def test_repo_url(mock_repo_config):
    repo = Repository(mock_repo_config, None)
    assert repo.repo_url == 'git@github.com:pre-commit/pre-commit-hooks'


def test_sha(mock_repo_config):
    repo = Repository(mock_repo_config, None)
    assert repo.sha == '5e713f8878b7d100c0e059f8cc34be4fc2e8f897'


@pytest.mark.integration
def test_languages(config_for_python_hooks_repo, store):
    repo = Repository.create(config_for_python_hooks_repo, store)
    assert repo.languages == set(['python'])


def test_reinstall(config_for_python_hooks_repo, store):
    repo = Repository.create(config_for_python_hooks_repo, store)
    repo.require_installed()
    # Reinstall with same repo should not trigger another install
    # TODO: how to assert this?
    repo.require_installed()
    # Reinstall on another run should not trigger another install
    # TODO: how to assert this?
    repo = Repository.create(config_for_python_hooks_repo, store)
    repo.require_installed()


@pytest.mark.integration
def test_really_long_file_paths(config_for_python_hooks_repo, store):
    path = 'really_long' * 10
    local['git']['init', path]()
    with local.cwd(path):
        repo = Repository.create(config_for_python_hooks_repo, store)
        repo.require_installed()
