from __future__ import annotations

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
    with store.connect() as db:
        return db.execute('SELECT COUNT(1) FROM repos').fetchone()[0]


def _config_count(store):
    with store.connect() as db:
        return db.execute('SELECT COUNT(1) FROM configs').fetchone()[0]


def _repo_refs(store):
    with store.connect() as db:
        return {ref for ref, in db.execute('SELECT ref FROM repos')}


def _repos_used_count(store):
    with store.connect() as db:
        return db.execute('SELECT COUNT(1) FROM repos_used').fetchone()[0]


def _install_revs(tempdir_factory, store, n):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    revs = [git.head_rev(path)]
    for _ in range(n - 1):
        git_commit(cwd=path)
        revs.append(git.head_rev(path))

    write_config('.', make_config_from_repo(path, rev=revs[0]))
    store.mark_config_used(C.CONFIG_FILE)
    assert not install_hooks(C.CONFIG_FILE, store)
    for rev in revs[1:]:
        with modify_config() as config:
            config['repos'][0]['rev'] = rev
        assert not install_hooks(C.CONFIG_FILE, store)
    return revs


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
    assert not install_hooks(C.CONFIG_FILE, store)
    assert not autoupdate(C.CONFIG_FILE, freeze=False, tags_only=False)
    assert not install_hooks(C.CONFIG_FILE, store)

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
    with store.connect() as db:
        path, = db.execute('SELECT path FROM repos').fetchone()
    os.remove(os.path.join(path, C.MANIFEST_FILE))

    assert _config_count(store) == 1
    assert _repo_count(store) == 1
    assert not gc(store)
    assert _config_count(store) == 1
    assert _repo_count(store) == 0
    assert cap_out.get().splitlines()[-1] == '1 repo(s) removed.'


def test_gc_pre_1_14_roll_forward(store, cap_out):
    with store.connect() as db:  # simulate pre-1.14.0
        db.executescript('DROP TABLE configs')

    assert not gc(store)
    assert cap_out.get() == '0 repo(s) removed.\n'


def test_gc_keep_retains_unreferenced_repos(
        tempdir_factory, store, in_git_dir, cap_out,
):
    old_rev, new_rev = _install_revs(tempdir_factory, store, 2)

    assert _repo_count(store) == 2
    # keep the unreferenced revision
    assert not gc(store, keep=2)
    assert _repo_refs(store) == {old_rev, new_rev}
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'

    # revisiting the old revision keeps the cache warm
    with modify_config() as config:
        config['repos'][0]['rev'] = old_rev
    assert not gc(store, keep=2)
    assert _repo_refs(store) == {old_rev, new_rev}

    # lowering the limit removes the unreferenced revision
    assert not gc(store, keep=1)
    assert _repo_refs(store) == {old_rev}
    assert _repos_used_count(store) == 1
    assert cap_out.get().splitlines()[-1] == '1 repo(s) removed.'


def test_gc_keep_evicts_least_recently_used(
        tempdir_factory, store, in_git_dir, cap_out,
):
    revs = _install_revs(tempdir_factory, store, 3)

    # mark revs[1], then revs[0] as used
    for rev in reversed(revs[:-1]):
        assert not gc(store, keep=3)
        with modify_config() as config:
            config['repos'][0]['rev'] = rev

    assert _repo_count(store) == 3
    assert not gc(store, keep=2)
    # revs[2] was cloned last but used least recently
    assert _repo_refs(store) == {revs[0], revs[1]}
    assert cap_out.get().splitlines()[-1] == '1 repo(s) removed.'


def test_gc_keep_falls_back_to_clone_order(
        tempdir_factory, store, in_git_dir, cap_out,
):
    revs = _install_revs(tempdir_factory, store, 3)

    assert _repo_count(store) == 3
    assert not gc(store, keep=2)
    assert _repo_refs(store) == {revs[1], revs[2]}
    assert cap_out.get().splitlines()[-1] == '1 repo(s) removed.'


def test_gc_keep_does_not_evict_referenced_repos(
        tempdir_factory, store, in_git_dir, cap_out,
):
    path = make_repo(tempdir_factory, 'script_hooks_repo')
    old_rev = git.head_rev(path)
    git_commit(cwd=path)
    new_rev = git.head_rev(path)

    # reference both revisions
    os.mkdir('other')
    write_config('.', make_config_from_repo(path, rev=old_rev))
    write_config('other', make_config_from_repo(path, rev=new_rev))
    store.mark_config_used(C.CONFIG_FILE)
    store.mark_config_used(os.path.join('other', C.CONFIG_FILE))
    assert not install_hooks(C.CONFIG_FILE, store)
    assert not install_hooks(os.path.join('other', C.CONFIG_FILE), store)

    assert _repo_count(store) == 2
    # referenced repos can exceed `keep`
    assert not gc(store, keep=1)
    assert _repo_refs(store) == {old_rev, new_rev}
    assert cap_out.get().splitlines()[-1] == '0 repo(s) removed.'


def test_gc_keep_removes_stale_usage_rows(store, cap_out):
    with store.connect() as db:
        db.execute(
            'INSERT INTO repos_used (repo, ref, gc_gen) VALUES (?, ?, ?)',
            ('repo', 'ref', 1),
        )

    assert not gc(store, keep=2)
    assert _repos_used_count(store) == 0
    assert cap_out.get() == '0 repo(s) removed.\n'


def test_gc_roll_forward_no_repos_used_table(store, cap_out):
    with store.connect() as db:  # simulate a store from an older version
        db.executescript('DROP TABLE repos_used')

    assert not gc(store, keep=2)
    assert cap_out.get() == '0 repo(s) removed.\n'
