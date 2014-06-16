from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pre_commit.manifest import Manifest
from testing.fixtures import make_repo
from testing.util import get_head_sha


@pytest.yield_fixture
def manifest(store, tmpdir_factory):
    path = make_repo(tmpdir_factory, 'script_hooks_repo')
    head_sha = get_head_sha(path)
    repo_path_getter = store.get_repo_path_getter(path, head_sha)
    yield Manifest(repo_path_getter)


def test_manifest_contents(manifest):
    # Should just retrieve the manifest contents
    assert manifest.manifest_contents == [{
        'description': '',
        'entry': 'bin/hook.sh',
        'expected_return_value': 0,
        'files': '',
        'id': 'bash_hook',
        'language': 'script',
        'language_version': 'default',
        'name': 'Bash hook',
    }]


def test_hooks(manifest):
    assert manifest.hooks['bash_hook'] == {
        'description': '',
        'entry': 'bin/hook.sh',
        'expected_return_value': 0,
        'files': '',
        'id': 'bash_hook',
        'language': 'script',
        'language_version': 'default',
        'name': 'Bash hook',
    }
