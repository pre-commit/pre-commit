from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pre_commit import git
from pre_commit.manifest import Manifest
from testing.fixtures import make_repo


@pytest.yield_fixture
def manifest(store, tempdir_factory):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    repo_path = store.clone(path, git.head_sha(path))
    yield Manifest(repo_path)


def test_manifest_contents(manifest):
    # Should just retrieve the manifest contents
    assert manifest.manifest_contents == [{
        'always_run': False,
        'additional_dependencies': [],
        'args': [],
        'description': '',
        'entry': 'bin/hook.sh',
        'exclude': '^$',
        'files': '',
        'id': 'bash_hook',
        'language': 'script',
        'language_version': 'default',
        'log_file': '',
        'minimum_pre_commit_version': '0',
        'name': 'Bash hook',
        'pass_filenames': True,
        'stages': [],
        'types': ['file'],
        'exclude_types': [],
    }]


def test_hooks(manifest):
    assert manifest.hooks['bash_hook'] == {
        'always_run': False,
        'additional_dependencies': [],
        'args': [],
        'description': '',
        'entry': 'bin/hook.sh',
        'exclude': '^$',
        'files': '',
        'id': 'bash_hook',
        'language': 'script',
        'language_version': 'default',
        'log_file': '',
        'minimum_pre_commit_version': '0',
        'name': 'Bash hook',
        'pass_filenames': True,
        'stages': [],
        'types': ['file'],
        'exclude_types': [],
    }


def test_default_python_language_version(store, tempdir_factory):
    path = make_repo(tempdir_factory, 'python_hooks_repo')
    repo_path = store.clone(path, git.head_sha(path))
    manifest = Manifest(repo_path)

    # This assertion is difficult as it is version dependent, just assert
    # that it is *something*
    assert manifest.hooks['foo']['language_version'] != 'default'
