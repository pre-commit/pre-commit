import os
import jsonschema
import pytest

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
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
def test_install_python_repo_in_env(python_pre_commit_git_repo, config_for_python_pre_commit_git_repo):
    repo = Repository(config_for_python_pre_commit_git_repo)
    repo.install()

    assert os.path.exists(
        os.path.join(
            python_pre_commit_git_repo,
            C.HOOKS_WORKSPACE,
            repo.sha,
            'py_env',
        ),
    )


@pytest.mark.integration
def test_run_a_python_hook(config_for_python_pre_commit_git_repo):
    repo = Repository(config_for_python_pre_commit_git_repo)
    repo.install()
    ret = repo.run_hook('foo', [])

    assert ret[0] == 0
    assert ret[1] == 'Hello World\n'


@pytest.mark.integration
def test_run_a_hook_lots_of_files(config_for_python_pre_commit_git_repo):
    repo = Repository(config_for_python_pre_commit_git_repo)
    repo.install()
    ret = repo.run_hook('foo', ['/dev/null'] * 15000)

    assert ret[0] == 0
    assert ret[1] == 'Hello World\n'


@pytest.mark.skipif(True, reason="TODO: make this test not super slow")
def test_run_a_node_hook(config_for_node_pre_commit_git_repo):
    repo = Repository(config_for_node_pre_commit_git_repo)
    repo.install()
    ret = repo.run_hook('foo', [])

    assert ret[0] == 0
    assert ret[1] == 'Hello World\n'

@pytest.fixture
def mock_repo_config():
    config = {
        'repo': 'git@github.com:pre-commit/pre-commit-hooks',
        'sha': '5e713f8878b7d100c0e059f8cc34be4fc2e8f897',
        'hooks': [{
            'id': 'pyflakes',
            'files': '*.py',
        }],
    }

    jsonschema.validate([config], CONFIG_JSON_SCHEMA)

    return config


def test_repo_url(mock_repo_config):
    repo = Repository(mock_repo_config)
    assert repo.repo_url == 'git@github.com:pre-commit/pre-commit-hooks'


def test_sha(mock_repo_config):
    repo = Repository(mock_repo_config)
    assert repo.sha == '5e713f8878b7d100c0e059f8cc34be4fc2e8f897'


@pytest.mark.integration
def test_languages(config_for_python_pre_commit_git_repo):
    repo = Repository(config_for_python_pre_commit_git_repo)
    assert repo.languages == set(['python'])



