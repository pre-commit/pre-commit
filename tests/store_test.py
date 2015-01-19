from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import os.path
import shutil
import sqlite3

import mock
import pytest

from pre_commit import five
from pre_commit.store import _get_default_directory
from pre_commit.store import logger
from pre_commit.store import Store
from pre_commit.util import cmd_output
from pre_commit.util import cwd
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
    io.open(store.db_path, 'a+').close()
    # Call require_created, this should not call create
    store.require_created()
    assert not os.path.exists(os.path.join(store.directory, 'README'))


@pytest.yield_fixture
def log_info_mock():
    with mock.patch.object(logger, 'info', autospec=True) as info_mock:
        yield info_mock


def test_clone(store, tmpdir_factory, log_info_mock):
    path = git_dir(tmpdir_factory)
    with cwd(path):
        cmd_output('git', 'commit', '--allow-empty', '-m', 'foo')
        sha = get_head_sha(path)
        cmd_output('git', 'commit', '--allow-empty', '-m', 'bar')

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

    # Assert there's an entry in the sqlite db for this
    with sqlite3.connect(store.db_path) as db:
        path, = db.execute(
            'SELECT path from repos WHERE repo = ? and ref = ?',
            [path, sha],
        ).fetchone()
        assert path == ret


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
    # Create an entry in the sqlite db that makes it look like the repo has
    # been cloned.
    store.require_created()

    with sqlite3.connect(store.db_path) as db:
        db.execute(
            'INSERT INTO repos (repo, ref, path) '
            'VALUES ("fake_repo", "fake_ref", "fake_path")'
        )

    assert store.clone('fake_repo', 'fake_ref') == 'fake_path'


def test_require_created_when_directory_exists_but_not_db(store):
    # In versions <= 0.3.5, there was no sqlite db causing a need for
    # backward compatibility
    os.makedirs(store.directory)
    store.require_created()
    assert os.path.exists(store.db_path)
