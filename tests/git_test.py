
import os
import pytest

from plumbum import local
from pre_commit import git

import pre_commit.constants as C

def add_and_commit():
    local['git']['add', '.']()
    local['git']['config', 'user.email', 'ken@struys.ca']
    local['git']['config', 'user.name', 'Ken Struys']
    local['git']['commit', '-m', 'random commit']()


def get_sha(git_repo):
    with local.cwd(git_repo):
        return (local['git']['log', '--format="%H"'] | local['head']['-n1'])().strip('"\n')

@pytest.yield_fixture
def dummy_git_repo(empty_git_dir):
    local['touch']['dummy']()
    add_and_commit()

    yield empty_git_dir


@pytest.yield_fixture
def dummy_pre_commit_hooks_git_repo(dummy_git_repo):
    local.path(C.MANIFEST_FILE).write("""
hooks:
    -
        id: foo
        name: Foo
        entry: foo
        language: python>2.6
    """)

    add_and_commit()

    yield dummy_git_repo

@pytest.yield_fixture
def python_pre_commit_git_repo(dummy_pre_commit_hooks_git_repo):
    local.path('setup.py').write(
"""
from setuptools import find_packages
from setuptools import setup

setup(
    name='Foo',
    version='0.0.0',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': [
            'entry = foo.main:func'
        ],
    }
)
"""
    )

    foo_module = local.path('foo')

    foo_module.mkdir()

    with local.cwd(foo_module):
        local.path('__init__.py').write('')
        local.path('main.py').write(
"""

def func():
    return 0

"""
        )

    add_and_commit()

    yield dummy_pre_commit_hooks_git_repo


def test_get_root(empty_git_dir):
    assert git.get_root() == empty_git_dir

    foo = local.path('foo')
    foo.mkdir()

    with local.cwd(foo):
        assert git.get_root() == empty_git_dir


def test_get_pre_commit_path(empty_git_dir):
    assert git.get_pre_commit_path() == '{0}/.git/hooks/pre-commit'.format(empty_git_dir)


def test_create_pre_commit(empty_git_dir):
    git.create_pre_commit()
    assert len(open(git.get_pre_commit_path(), 'r').read()) > 0


def test_remove_pre_commit(empty_git_dir):
    git.remove_pre_commit()

    assert not os.path.exists(git.get_pre_commit_path())

    git.create_pre_commit()
    git.remove_pre_commit()

    assert not os.path.exists(git.get_pre_commit_path())


def test_create_repo_in_env(empty_git_dir, dummy_git_repo):
    sha = get_sha(dummy_git_repo)
    git.create_repo_in_env(dummy_git_repo, sha)
    assert os.path.exists(os.path.join(dummy_git_repo, C.PRE_COMMIT_DIR, sha))


@pytest.mark.integration
def test_install_python_repo_in_env(empty_git_dir, python_pre_commit_git_repo):
    sha = get_sha(python_pre_commit_git_repo)
    git.install_pre_commit(python_pre_commit_git_repo,  sha)
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
        git.install_pre_commit(repo['repo'], repo['sha'])

    print python_pre_commit_git_repo