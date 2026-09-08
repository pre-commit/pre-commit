from __future__ import annotations

import collections
import heapq
import os.path
import sqlite3
from typing import Any

import pre_commit.constants as C
from pre_commit import output
from pre_commit.clientlib import InvalidConfigError
from pre_commit.clientlib import InvalidManifestError
from pre_commit.clientlib import load_config
from pre_commit.clientlib import load_manifest
from pre_commit.clientlib import LOCAL
from pre_commit.clientlib import META
from pre_commit.store import Store
from pre_commit.util import rmtree


def _mark_used_repos(
        store: Store,
        all_repos: dict[tuple[str, str], str],
        unused_repos: set[tuple[str, str]],
        repo: dict[str, Any],
) -> None:
    if repo['repo'] == META:
        return
    elif repo['repo'] == LOCAL:
        for hook in repo['hooks']:
            deps = hook.get('additional_dependencies')
            unused_repos.discard((
                store.db_repo_name(repo['repo'], deps),
                C.LOCAL_REPO_VERSION,
            ))
    else:
        key = (repo['repo'], repo['rev'])
        path = all_repos.get(key)
        # can't inspect manifest if it isn't cloned
        if path is None:
            return

        try:
            manifest = load_manifest(os.path.join(path, C.MANIFEST_FILE))
        except InvalidManifestError:
            return
        else:
            unused_repos.discard(key)
            by_id = {hook['id']: hook for hook in manifest}

        for hook in repo['hooks']:
            if hook['id'] not in by_id:
                continue

            deps = hook.get(
                'additional_dependencies',
                by_id[hook['id']]['additional_dependencies'],
            )
            unused_repos.discard((
                store.db_repo_name(repo['repo'], deps), repo['rev'],
            ))


def _next_gc_gen(db: sqlite3.Connection) -> int:
    gen, = db.execute(
        'SELECT COALESCE(MAX(gc_gen), 0) FROM repos_used',
    ).fetchone()
    return gen + 1


def _keep_unused(
        keep: int,
        used_repos: set[tuple[str, str]],
        unused_repos: set[tuple[str, str]],
        last_used: dict[tuple[str, str], tuple[int, int]],
) -> set[tuple[str, str]]:
    n_used = collections.Counter(repo for repo, _ in used_repos)
    by_repo: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for key in unused_repos:
        by_repo[key[0]].append(key)

    ret = set()
    for repo, keys in by_repo.items():
        n = keep - n_used[repo]
        if n > 0:
            ret.update(heapq.nlargest(n, keys, key=last_used.__getitem__))
    return ret


def _gc(store: Store, keep: int) -> int:
    with store.exclusive_lock(), store.connect() as db:
        store._create_configs_table(db)
        store._create_repos_used_table(db)

        repos = db.execute(
            'SELECT repos.repo, repos.ref, path, repos.rowid, '
            '       COALESCE(gc_gen, 0) '
            'FROM repos LEFT JOIN repos_used USING (repo, ref)',
        ).fetchall()
        all_repos = {
            (repo, ref): path for repo, ref, path, _, _ in repos
        }
        unused_repos = set(all_repos)

        configs_rows = db.execute('SELECT path FROM configs').fetchall()
        configs = [path for path, in configs_rows]

        dead_configs = []
        for config_path in configs:
            try:
                config = load_config(config_path)
            except InvalidConfigError:
                dead_configs.append(config_path)
                continue
            else:
                for repo in config['repos']:
                    _mark_used_repos(store, all_repos, unused_repos, repo)

        paths = [(path,) for path in dead_configs]
        db.executemany('DELETE FROM configs WHERE path = ?', paths)

        # track recency across `gc` runs
        used_repos = set(all_repos) - unused_repos
        gc_gen = _next_gc_gen(db)
        db.executemany(
            'INSERT OR REPLACE INTO repos_used (repo, ref, gc_gen) '
            'VALUES (?, ?, ?)',
            [(repo, ref, gc_gen) for repo, ref in sorted(used_repos)],
        )

        if keep:
            last_used = {
                (repo, ref): (gc_gen, rowid)
                for repo, ref, _, rowid, gc_gen in repos
            }
            unused_repos -= _keep_unused(
                keep, used_repos, unused_repos, last_used,
            )

        db.executemany(
            'DELETE FROM repos WHERE repo = ? and ref = ?',
            sorted(unused_repos),
        )
        db.execute(
            'DELETE FROM repos_used WHERE NOT EXISTS ('
            '    SELECT 1 FROM repos'
            '    WHERE repos.repo = repos_used.repo'
            '      AND repos.ref = repos_used.ref'
            ')',
        )
        for k in unused_repos:
            rmtree(all_repos[k])

        return len(unused_repos)


def gc(store: Store, keep: int = 0) -> int:
    output.write_line(f'{_gc(store, keep)} repo(s) removed.')
    return 0
