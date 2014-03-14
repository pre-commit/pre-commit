import os

import jsonschema
import pytest
from pre_commit import git

import pre_commit.constants as C
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.repo_installer import RepoInstaller


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
    repo_installer = RepoInstaller(dummy_repo_config)
    repo_installer.create()

    assert os.path.exists(
        os.path.join(dummy_git_repo, C.HOOKS_WORKSPACE, repo_installer.sha),
    )

@pytest.mark.integration
def test_install_python_repo_in_env(python_pre_commit_git_repo, config_for_python_pre_commit_git_repo):
    repo_installer = RepoInstaller(config_for_python_pre_commit_git_repo)
    # TODO: do we need create here?
    repo_installer.install()

    assert os.path.exists(
        os.path.join(
            python_pre_commit_git_repo,
            C.HOOKS_WORKSPACE,
            repo_installer.sha,
            'py_env',
        ),
    )


@pytest.fixture
def simple_config(python_pre_commit_git_repo):
    config = [
        {
            'repo': python_pre_commit_git_repo,
            'sha': git.get_head_sha(python_pre_commit_git_repo),
            'hooks': [
                {
                    'id': 'foo',
                    'files': '*.py',
                },
            ],
        },
    ]
    jsonschema.validate(config, CONFIG_JSON_SCHEMA)
    return config
