import os.path
import sqlite3
from unittest import mock

import pytest

from pre_commit import git
from pre_commit.store import _get_default_directory
from pre_commit.store import Store
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from testing.fixtures import git_dir
from testing.util import cwd
from testing.util import git_commit


def test_our_session_fixture_works():
    """There's a session fixture which makes `Store` invariantly raise to
    prevent writing to the home directory.
    """
    with pytest.raises(AssertionError):
        Store()


def test_get_default_directory_defaults_to_home():
    # Not we use the module level one which is not mocked
    ret = _get_default_directory()
    assert ret == os.path.join(os.path.expanduser('~/.cache'), 'pre-commit')


def test_adheres_to_xdg_specification():
    with mock.patch.dict(
        os.environ, {'XDG_CACHE_HOME': '/tmp/fakehome'},
    ):
        ret = _get_default_directory()
        assert ret == os.path.join('/tmp/fakehome', 'pre-commit')


def test_uses_environment_variable_when_present():
    with mock.patch.dict(
        os.environ, {'PRE_COMMIT_HOME': '/tmp/pre_commit_home'},
    ):
        ret = _get_default_directory()
        assert ret == '/tmp/pre_commit_home'


def test_store_init(store):
    # Should create the store directory
    assert os.path.exists(store.directory)
    # Should create a README file indicating what the directory is about
    with open(os.path.join(store.directory, 'README')) as readme_file:
        readme_contents = readme_file.read()
        for text_line in (
            'This directory is maintained by the pre-commit project.',
            'Learn more: https://github.com/pre-commit/pre-commit',
        ):
            assert text_line in readme_contents


def test_clone(store, tempdir_factory, log_info_mock):
    path = git_dir(tempdir_factory)
    with cwd(path):
        git_commit()
        rev = git.head_rev(path)
        git_commit()

    ret = store.clone(path, rev)
    # Should have printed some stuff
    assert log_info_mock.call_args_list[0][0][0].startswith(
        'Initializing environment for ',
    )

    # Should return a directory inside of the store
    assert os.path.exists(ret)
    assert ret.startswith(store.directory)
    # Directory should start with `repo`
    _, dirname = os.path.split(ret)
    assert dirname.startswith('repo')
    # Should be checked out to the rev we specified
    assert git.head_rev(ret) == rev

    # Assert there's an entry in the sqlite db for this
    assert store.select_all_repos() == [(path, rev, ret)]


def test_clone_cleans_up_on_checkout_failure(store):
    with pytest.raises(Exception) as excinfo:
        # This raises an exception because you can't clone something that
        # doesn't exist!
        store.clone('/i_dont_exist_lol', 'fake_rev')
    assert '/i_dont_exist_lol' in str(excinfo.value)

    repo_dirs = [
        d for d in os.listdir(store.directory) if d.startswith('repo')
    ]
    assert repo_dirs == []


def test_clone_when_repo_already_exists(store):
    # Create an entry in the sqlite db that makes it look like the repo has
    # been cloned.
    with sqlite3.connect(store.db_path) as db:
        db.execute(
            'INSERT INTO repos (repo, ref, path) '
            'VALUES ("fake_repo", "fake_ref", "fake_path")',
        )

    assert store.clone('fake_repo', 'fake_ref') == 'fake_path'


def test_clone_shallow_failure_fallback_to_complete(
    store, tempdir_factory,
    log_info_mock,
):
    path = git_dir(tempdir_factory)
    with cwd(path):
        git_commit()
        rev = git.head_rev(path)
        git_commit()

    # Force shallow clone failure
    def fake_shallow_clone(self, *args, **kwargs):
        raise CalledProcessError(None, None, None, None, None)
    store._shallow_clone = fake_shallow_clone

    ret = store.clone(path, rev)

    # Should have printed some stuff
    assert log_info_mock.call_args_list[0][0][0].startswith(
        'Initializing environment for ',
    )

    # Should return a directory inside of the store
    assert os.path.exists(ret)
    assert ret.startswith(store.directory)
    # Directory should start with `repo`
    _, dirname = os.path.split(ret)
    assert dirname.startswith('repo')
    # Should be checked out to the rev we specified
    assert git.head_rev(ret) == rev

    # Assert there's an entry in the sqlite db for this
    assert store.select_all_repos() == [(path, rev, ret)]


def test_clone_tag_not_on_mainline(store, tempdir_factory):
    path = git_dir(tempdir_factory)
    with cwd(path):
        git_commit()
        cmd_output('git', 'checkout', 'master', '-b', 'branch')
        git_commit()
        cmd_output('git', 'tag', 'v1')
        cmd_output('git', 'checkout', 'master')
        cmd_output('git', 'branch', '-D', 'branch')

    # previously crashed on unreachable refs
    store.clone(path, 'v1')


def test_create_when_directory_exists_but_not_db(store):
    # In versions <= 0.3.5, there was no sqlite db causing a need for
    # backward compatibility
    os.remove(store.db_path)
    store = Store(store.directory)
    assert os.path.exists(store.db_path)


def test_create_when_store_already_exists(store):
    # an assertion that this is idempotent and does not crash
    Store(store.directory)


def test_db_repo_name(store):
    assert store.db_repo_name('repo', ()) == 'repo'
    assert store.db_repo_name('repo', ('b', 'a', 'c')) == 'repo:a,b,c'


def test_local_resources_reflects_reality():
    on_disk = {
        res[len('empty_template_'):]
        for res in os.listdir('pre_commit/resources')
        if res.startswith('empty_template_')
    }
    assert on_disk == set(Store.LOCAL_RESOURCES)


def test_mark_config_as_used(store, tmpdir):
    with tmpdir.as_cwd():
        f = tmpdir.join('f').ensure()
        store.mark_config_used('f')
        assert store.select_all_configs() == [f.strpath]


def test_mark_config_as_used_idempotent(store, tmpdir):
    test_mark_config_as_used(store, tmpdir)
    test_mark_config_as_used(store, tmpdir)


def test_mark_config_as_used_does_not_exist(store):
    store.mark_config_used('f')
    assert store.select_all_configs() == []


def _simulate_pre_1_14_0(store):
    with store.connect() as db:
        db.executescript('DROP TABLE configs')


def test_select_all_configs_roll_forward(store):
    _simulate_pre_1_14_0(store)
    assert store.select_all_configs() == []


def test_mark_config_as_used_roll_forward(store, tmpdir):
    _simulate_pre_1_14_0(store)
    test_mark_config_as_used(store, tmpdir)
