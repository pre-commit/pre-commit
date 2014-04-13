import mock
import os
import pytest

import pre_commit.constants as C
from pre_commit import git
from pre_commit import repository
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from pre_commit.prefixed_command_runner import PrefixedCommandRunner
from pre_commit.repository import Repository


@pytest.fixture
def dummy_repo_config(dummy_git_repo):
    # This is not a valid config, but it is pretty close
    return {
        'repo': dummy_git_repo,
        'sha': git.get_head_sha(dummy_git_repo),
        'hooks': [],
    }


@pytest.mark.integration
def test_create_repo_in_env(dummy_repo_config, dummy_git_repo):
    repo = Repository(dummy_repo_config)
    repo.create()

    assert os.path.exists(
        os.path.join(dummy_git_repo, C.HOOKS_WORKSPACE, repo.sha),
    )


@pytest.mark.integration
def test_install_python_repo_in_env(config_for_python_hooks_repo):
    repo = Repository(config_for_python_hooks_repo)
    repo.install(PrefixedCommandRunner(C.HOOKS_WORKSPACE))

    assert os.path.exists(
        os.path.join(
            repo.repo_url,
            C.HOOKS_WORKSPACE,
            repo.sha,
            'py_env',
        ),
    )


@pytest.mark.integration
def test_run_a_python_hook(config_for_python_hooks_repo):
    repo = Repository(config_for_python_hooks_repo)
    ret = repo.run_hook(
        PrefixedCommandRunner(C.HOOKS_WORKSPACE), 'foo', ['/dev/null'],
    )

    assert ret[0] == 0
    assert ret[1] == b"['/dev/null']\nHello World\n"


@pytest.mark.integration
def test_run_a_hook_lots_of_files(config_for_python_hooks_repo):
    repo = Repository(config_for_python_hooks_repo)
    ret = repo.run_hook(
        PrefixedCommandRunner(C.HOOKS_WORKSPACE), 'foo', ['/dev/null'] * 15000,
    )

    assert ret[0] == 0


@pytest.mark.integration
def test_cwd_of_hook(config_for_prints_cwd_repo):
    # Note: this doubles as a test for `system` hooks
    repo = Repository(config_for_prints_cwd_repo)
    ret = repo.run_hook(
        PrefixedCommandRunner(C.HOOKS_WORKSPACE), 'prints_cwd', [],
    )

    assert ret[0] == 0
    assert ret[1] == repo.repo_url.encode('utf-8') + b'\n'


@pytest.mark.skipif(
    os.environ.get('slowtests', None) == 'false',
    reason="TODO: make this test not super slow",
)
@pytest.mark.integration
def test_run_a_node_hook(config_for_node_hooks_repo):
    repo = Repository(config_for_node_hooks_repo)
    ret = repo.run_hook(PrefixedCommandRunner(C.HOOKS_WORKSPACE), 'foo', [])

    assert ret[0] == 0
    assert ret[1] == b'Hello World\n'


@pytest.mark.integration
def test_run_a_script_hook(config_for_script_hooks_repo):
    repo = Repository(config_for_script_hooks_repo)
    ret = repo.run_hook(
        PrefixedCommandRunner(C.HOOKS_WORKSPACE), 'bash_hook', ['bar'],
    )

    assert ret[0] == 0
    assert ret[1] == b'bar\nHello World\n'


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
    repo = Repository(mock_repo_config)
    assert repo.repo_url == 'git@github.com:pre-commit/pre-commit-hooks'


def test_sha(mock_repo_config):
    repo = Repository(mock_repo_config)
    assert repo.sha == '5e713f8878b7d100c0e059f8cc34be4fc2e8f897'


@pytest.mark.integration
def test_languages(config_for_python_hooks_repo):
    repo = Repository(config_for_python_hooks_repo)
    assert repo.languages == set(['python'])


@pytest.yield_fixture
def logger_mock():
    with mock.patch.object(
        repository.logger, 'info', autospec=True,
    ) as info_mock:
        yield info_mock


def test_prints_while_creating(config_for_python_hooks_repo, logger_mock):
    repo = Repository(config_for_python_hooks_repo)
    repo.require_created()
    logger_mock.assert_called_with('This may take a few minutes...')
    logger_mock.reset_mock()
    # Reinstall with same repo should not trigger another install
    repo.require_created()
    assert logger_mock.call_count == 0
    # Reinstall on another run should not trigger another install
    repo = Repository(config_for_python_hooks_repo)
    repo.require_created()
    assert logger_mock.call_count == 0


def test_reinstall(config_for_python_hooks_repo):
    repo = Repository(config_for_python_hooks_repo)
    repo.require_installed(PrefixedCommandRunner(C.HOOKS_WORKSPACE))
    # Reinstall with same repo should not trigger another install
    # TODO: how to assert this?
    repo.require_installed(PrefixedCommandRunner(C.HOOKS_WORKSPACE))
    # Reinstall on another run should not trigger another install
    # TODO: how to assert this?
    repo = Repository(config_for_python_hooks_repo)
    repo.require_installed(PrefixedCommandRunner(C.HOOKS_WORKSPACE))
