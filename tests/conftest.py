from __future__ import absolute_import

import jsonschema
import pytest
import time
from plumbum import local

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA


@pytest.yield_fixture
def empty_git_dir(tmpdir):
    with local.cwd(tmpdir.strpath):
        local['git']['init']()
        yield tmpdir.strpath


def add_and_commit():
    local['git']['add', '.']()
    local['git']['commit', '-m', 'random commit {0}'.format(time.time())]()


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
    local.path('setup.py').write("""
from setuptools import find_packages
from setuptools import setup

setup(
    name='Foo',
    version='0.0.0',
    packages=find_packages('.'),
    entry_points={
        'console_scripts': [
            'foo = foo.main:func'
        ],
    }
)
"""
    )

    foo_module = local.path('foo')

    foo_module.mkdir()

    with local.cwd(foo_module):
        local.path('__init__.py').write('')
        local.path('main.py').write("""
def func():
    return 0
"""
        )

    add_and_commit()

    yield dummy_pre_commit_hooks_git_repo


@pytest.fixture
def config_for_python_pre_commit_git_repo(python_pre_commit_git_repo):
    config = {
        'repo': python_pre_commit_git_repo,
        'sha': git.get_head_sha(python_pre_commit_git_repo),
        'hooks': [{
            'id': 'foo',
            'files': '*.py',
        }],
    }

    jsonschema.validate([config], CONFIG_JSON_SCHEMA)

    return config