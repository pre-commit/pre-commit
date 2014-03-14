import pytest
import os

import pre_commit.constants as C
from plumbum import local
from pre_commit.installer.repo_installer import create_repo_in_env
from pre_commit.installer.repo_installer import install_pre_commit


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


@pytest.mark.integration
def test_install_config(empty_git_dir, python_pre_commit_git_repo):

    config = [
        {
            'repo': python_pre_commit_git_repo,
            'sha': get_sha(python_pre_commit_git_repo),
            'hooks': [
                {
                    'id': 'foo',
                    'args': [
                        {
                            'type': 'files',
                            'opt': '*.py'
                        },
                        ]
                }
            ],
            },
        ]
    for repo in config:
        install_pre_commit(repo['repo'], repo['sha'])

    assert os.path.exists(os.path.join(python_pre_commit_git_repo, C.PRE_COMMIT_DIR, config[0]['sha'], 'py_env'))