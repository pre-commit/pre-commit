from __future__ import absolute_import
from __future__ import unicode_literals

import hashlib
import io
import mock
import os
import os.path
import pytest
import shutil
from plumbum import local

from pre_commit import five
from pre_commit.store import _get_default_directory
from pre_commit.store import logger
from pre_commit.store import Store
from testing.fixtures import git_dir
from testing.util import get_head_sha


def test_our_session_fixture_works():
    """There's a session fixture which makes `Store` invariantly raise to
    prevent writing to the home directory.
    """
    with pytest.raises(AssertionError):
        Store()


def test_get_default_directory_defaults_to_home():
    # Not we use the module level one which is not mocked
    ret = _get_default_directory()
    assert ret == os.path.join(os.environ['HOME'], '.pre-commit')


def test_uses_environment_variable_when_present():
    with mock.patch.dict(
        os.environ, {'PRE_COMMIT_HOME': '/tmp/pre_commit_home'}
    ):
        ret = _get_default_directory()
        assert ret == '/tmp/pre_commit_home'


def test_store_require_created(store):
    assert not os.path.exists(store.directory)
    store.require_created()
    # Should create the store directory
    assert os.path.exists(store.directory)
    # Should create a README file indicating what the directory is about
    with io.open(os.path.join(store.directory, 'README'), 'r') as readme_file:
        readme_contents = readme_file.read()
        for text_line in (
            'This directory is maintained by the pre-commit project.',
            'Learn more: https://github.com/pre-commit/pre-commit',
        ):
            assert text_line in readme_contents


def test_store_require_created_does_not_create_twice(store):
    assert not os.path.exists(store.directory)
    store.require_created()
    # We intentionally delete the directory here so we can figure out if it
    # calls it again.
    shutil.rmtree(store.directory)
    assert not os.path.exists(store.directory)
    # Call require_created, this should not trigger a call to create
    store.require_created()
    assert not os.path.exists(store.directory)


def test_does_not_recreate_if_directory_already_exists(store):
    assert not os.path.exists(store.directory)
    # We manually create the directory.
    # Note: we're intentionally leaving out the README file.  This is so we can
    # know that `Store` didn't call create
    os.mkdir(store.directory)
    # Call require_created, this should not call create
    store.require_created()
    assert not os.path.exists(os.path.join(store.directory, 'README'))


@pytest.yield_fixture
def log_info_mock():
    with mock.patch.object(logger, 'info', autospec=True) as info_mock:
        yield info_mock


def test_clone(store, tmpdir_factory, log_info_mock):
    path = git_dir(tmpdir_factory)
    with local.cwd(path):
        local['git']('commit', '--allow-empty', '-m', 'foo')
        sha = get_head_sha(path)
        local['git']('commit', '--allow-empty', '-m', 'bar')

    ret = store.clone(path, sha)
    # Should have printed some stuff
    log_info_mock.assert_called_with('This may take a few minutes...')

    # Should return a directory inside of the store
    assert os.path.exists(ret)
    assert ret.startswith(store.directory)
    # Directory should start with `repo`
    _, dirname = os.path.split(ret)
    assert dirname.startswith('repo')
    # Should be checked out to the sha we specified
    assert get_head_sha(ret) == sha

    # Assert that we made a symlink from the sha to the repo
    sha_path = os.path.join(
        store.directory, sha + '_' + hashlib.md5(path).hexdigest(),
    )
    assert os.path.exists(sha_path)
    assert os.path.islink(sha_path)
    assert os.readlink(sha_path) == ret


def test_clone_cleans_up_on_checkout_failure(store):
    try:
        # This raises an exception because you can't clone something that
        # doesn't exist!
        store.clone('/i_dont_exist_lol', 'fake_sha')
    except Exception as e:
        assert '/i_dont_exist_lol' in five.text(e)

    things_starting_with_repo = [
        thing for thing in os.listdir(store.directory)
        if thing.startswith('repo')
    ]
    assert things_starting_with_repo == []


def test_has_cmd_runner_at_directory(store):
    ret = store.cmd_runner
    assert ret.prefix_dir == store.directory + os.sep


def test_clone_when_repo_already_exists(store):
    # Create a symlink and directory in the store simulating an already
    # created repository.
    store.require_created()
    repo_dir_path = os.path.join(store.directory, 'repo_dir')
    os.mkdir(repo_dir_path)
    os.symlink(
        repo_dir_path,
        os.path.join(
            store.directory, 'fake_sha' + '_' + hashlib.md5('url').hexdigest(),
        ),
    )

    ret = store.clone('url', 'fake_sha')
    assert ret == repo_dir_path
