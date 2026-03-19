from __future__ import annotations

import json
import os.path
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


def _mark_used(
        config: dict[str, Any],
        repo: dict[str, Any],
        manifests: dict[tuple[str, str], dict[str, Any]],
        unused_manifests: set[tuple[str, str]],
        unused_installs: set[str],
) -> None:
    if repo['repo'] == META:
        return
    elif repo['repo'] == LOCAL:
        for hook in repo['hooks']:
            deps = hook['additional_dependencies']
            unused_installs.discard((
                repo['repo'], C.LOCAL_REPO_VERSION,
                repo['language'],
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
            by_id = manifest['hooks']

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


def _gc(store: Store) -> int:
    with store.exclusive_lock(), store.connect() as db:
        installs_rows = db.execute('SELECT key, path FROM installs').fetchall()
        all_installs = dict(installs_rows)
        unused_installs = set(all_installs)

        manifests_query = 'SELECT repo, rev, manifest FROM manifests'
        manifests = {
            (repo, rev): json.loads(manifest)
            for repo, rev, manifest in db.execute(manifests_query).fetchall()
        }
        unused_manifests = set(manifests)

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
                    _mark_used(
                        config,
                        repo,
                        manifests,
                        unused_manifests,
                        unused_installs,
                    )

        paths = [(path,) for path in dead_configs]
        db.executemany('DELETE FROM configs WHERE path = ?', paths)

        db.executemany(
            'DELETE FROM repos WHERE repo = ? and ref = ?',
            sorted(unused_repos),
        )
        for k in unused_repos:
            rmtree(all_repos[k])

        return len(unused_repos)


def gc(store: Store) -> int:
    installs, clones = _gc(store)
    output.write_line(f'{clones} clone(s) removed.')
    output.write_line(f'{installs} installs(s) removed.')
    return 0
