
import pytest
import pre_commit.constants as C
from plumbum import local


@pytest.yield_fixture
def empty_git_dir(tmpdir):
    with local.cwd(tmpdir.strpath):
        local['git']['init']()
        yield tmpdir.strpath



def add_and_commit():
    local['git']['add', '.']()
    local['git']['commit', '-m', 'random commit', '--author', 'A U Thor <author@example.com>']()


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
