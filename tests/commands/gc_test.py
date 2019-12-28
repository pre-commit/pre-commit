import os

import pre_commit.constants as C
from pre_commit import git
from pre_commit.clientlib import load_config
from pre_commit.commands.autoupdate import autoupdate
from pre_commit.commands.gc import gc
from pre_commit.commands.install_uninstall import install_hooks
from pre_commit.repository import all_hooks
from testing.fixtures import make_config_from_repo
from testing.fixtures import make_repo
from testing.fixtures import modify_config
from testing.fixtures import sample_local_config
from testing.fixtures import sample_meta_config
from testing.fixtures import write_config
from testing.util import git_commit


def _repo_count(store):
    return len(store.select_all_repos())


def _config_count(store):
    return len(store.select_all_configs())


def _remove_config_assert_cleared(store, cap_out):
    os.remove(C.CONFIG_FILE)
    assert not gc(store)
    assert _config_count(store) == 0
    assert _repo_count(store) == 0
    assert cap_out.get().splitlines()[-1] == '1 repo(s) removed.'


def test_gc(tempdir_factory, store, in_git_dir, cap_out):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    old_rev = git.head_rev(path)
    git_commit(cwd=path)

    write_config('.', make_config_from_repo(path, rev=old_rev))
    store.mark_config_used(C.CONFIG_FILE)

    # update will clone both the old and new repo, making the old one gc-able
    install_hooks(C.CONFIG_FILE, store)
    assert not autoupdate(C.CONFIG_FILE, store, freeze=False, tags_only=False)

    assert _config_count(store) == 1
    assert _repo_count(store) == 2
    assert not gc(store)
    assert _config_count(store) == 1
    assert _repo_count(store) == 1
    assert cap_out.get().splitlines()[-1] == '1 repo(s) removed.'

    _remove_config_assert_cleared(store, cap_out)


def test_gc_repo_not_cloned(tempdir_factory, store, in_git_dir, cap_out):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    write_config('.', make_config_from_repo(path))
    store.mark_config_used(C.CONFIG_FILE)

    assert _config_count(store) == 1
    assert _repo_count(store) == 0
    assert not gc(store)
    assert _config_count(store) == 1
    assert _repo_count(store) == 0
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'


def test_gc_meta_repo_does_not_crash(store, in_git_dir, cap_out):
    write_config('.', sample_meta_config())
    store.mark_config_used(C.CONFIG_FILE)
    assert not gc(store)
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'


def test_gc_local_repo_does_not_crash(store, in_git_dir, cap_out):
    write_config('.', sample_local_config())
    store.mark_config_used(C.CONFIG_FILE)
    assert not gc(store)
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'


def test_gc_unused_local_repo_with_env(store, in_git_dir, cap_out):
    config = {
        'repo': 'local',
        'hooks': [{
            'id': 'flake8', 'name': 'flake8', 'entry': 'flake8',
            # a `language: python` local hook will create an environment
            'types': ['python'], 'language': 'python',
        }],
    }
    write_config('.', config)
    store.mark_config_used(C.CONFIG_FILE)

    # this causes the repositories to be created
    all_hooks(load_config(C.CONFIG_FILE), store)

    assert _config_count(store) == 1
    assert _repo_count(store) == 1
    assert not gc(store)
    assert _config_count(store) == 1
    assert _repo_count(store) == 1
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'

    _remove_config_assert_cleared(store, cap_out)


def test_gc_config_with_missing_hook(
        tempdir_factory, store, in_git_dir, cap_out,
):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    write_config('.', make_config_from_repo(path))
    store.mark_config_used(C.CONFIG_FILE)
    # to trigger a clone
    all_hooks(load_config(C.CONFIG_FILE), store)

    with modify_config() as config:
        # add a hook which does not exist, make sure we don't crash
        config['repos'][0]['hooks'].append({'id': 'does-not-exist'})

    assert _config_count(store) == 1
    assert _repo_count(store) == 1
    assert not gc(store)
    assert _config_count(store) == 1
    assert _repo_count(store) == 1
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'

    _remove_config_assert_cleared(store, cap_out)


def test_gc_deletes_invalid_configs(store, in_git_dir, cap_out):
    config = {'i am': 'invalid'}
    write_config('.', config)
    store.mark_config_used(C.CONFIG_FILE)

    assert _config_count(store) == 1
    assert not gc(store)
    assert _config_count(store) == 0
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'


def test_invalid_manifest_gcd(tempdir_factory, store, in_git_dir, cap_out):
    # clean up repos from old pre-commit versions
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    write_config('.', make_config_from_repo(path))
    store.mark_config_used(C.CONFIG_FILE)

    # trigger a clone
    install_hooks(C.CONFIG_FILE, store)

    # we'll "break" the manifest to simulate an old version clone
    (_, _, path), = store.select_all_repos()
    os.remove(os.path.join(path, C.MANIFEST_FILE))

    assert _config_count(store) == 1
    assert _repo_count(store) == 1
    assert not gc(store)
    assert _config_count(store) == 1
    assert _repo_count(store) == 0
    assert cap_out.get().splitlines()[-1] == '1 repo(s) removed.'
