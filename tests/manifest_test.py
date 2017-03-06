from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pre_commit.manifest import Manifest
from testing.fixtures import make_repo
from testing.util import get_head_sha


@pytest.yield_fixture
def manifest(store, tempdir_factory):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    head_sha = get_head_sha(path)
    repo_path = store.clone(path, head_sha)
    yield Manifest(repo_path, path)


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
        'minimum_pre_commit_version': '0',
        'name': 'Bash hook',
        'stages': [],
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
        'minimum_pre_commit_version': '0',
        'name': 'Bash hook',
        'stages': [],
    }


def test_legacy_manifest_warn(store, tempdir_factory, log_warning_mock):
    path = make_repo(tempdir_factory, 'legacy_hooks_yaml_repo')
    head_sha = get_head_sha(path)
    repo_path = store.clone(path, head_sha)
    Manifest(repo_path, path).manifest_contents

    # Should have printed a warning
    assert log_warning_mock.call_args_list[0][0][0] == (
        '{} uses legacy hooks.yaml to provide hooks.\n'
        'In newer versions, this file is called .pre-commit-hooks.yaml\n'
        'This will work in this version of pre-commit but will be removed at '
        'a later time.\n'
        'If `pre-commit autoupdate` does not silence this warning consider '
        'making an issue / pull request.'.format(path)
    )
