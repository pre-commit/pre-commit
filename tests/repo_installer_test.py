import os

import jsonschema
import pytest
from plumbum import local

import pre_commit.constants as C
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.repo_installer import create_repo_in_env
from pre_commit.repo_installer import install_pre_commit


def get_sha(git_repo):
    with local.cwd(git_repo):
        return (local['git']['log', '--format="%H"'] | local['head']['-n1'])().strip('"\n')

@pytest.mark.integration
def test_create_repo_in_env(empty_git_dir, dummy_git_repo):
    sha = get_sha(dummy_git_repo)
    create_repo_in_env(dummy_git_repo, sha)

    assert os.path.exists(os.path.join(dummy_git_repo, C.PRE_COMMIT_DIR, sha))

@pytest.mark.integration
def test_install_python_repo_in_env(empty_git_dir, python_pre_commit_git_repo):
    sha = get_sha(python_pre_commit_git_repo)
    install_pre_commit(python_pre_commit_git_repo,  sha)

    assert os.path.exists(os.path.join(python_pre_commit_git_repo, C.PRE_COMMIT_DIR, sha, 'py_env'))


@pytest.fixture
def simple_config(python_pre_commit_git_repo):
    config = [
        {
            'repo': python_pre_commit_git_repo,
            'sha': get_sha(python_pre_commit_git_repo),
            'hooks': [
                {
                    'id': 'foo',
                    'files': '*.py',
                    }
            ],
        },
    ]
    jsonschema.validate(config, CONFIG_JSON_SCHEMA)
    return config


@pytest.mark.integration
def test_install_config(empty_git_dir, python_pre_commit_git_repo, simple_config):
    for repo in simple_config:
        install_pre_commit(repo['repo'], repo['sha'])

    assert os.path.exists(
        os.path.join(
            python_pre_commit_git_repo,
            C.PRE_COMMIT_DIR, simple_config[0]['sha'],
            'py_env',
        ),
    )