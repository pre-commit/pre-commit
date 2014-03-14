import os

import pytest
from pre_commit import git

import pre_commit.constants as C
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
    # TODO: do we need create here?
    repo.install()

    assert os.path.exists(
        os.path.join(
            python_pre_commit_git_repo,
            C.HOOKS_WORKSPACE,
            repo.sha,
            'py_env',
        ),
    )
