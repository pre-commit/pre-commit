from __future__ import annotations

import os.path
import re
import tempfile
from concurrent.futures import as_completed
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from typing import cast
from typing import List
from typing import NamedTuple
from typing import Sequence
from typing import Union

import pre_commit.constants as C
from pre_commit import git
from pre_commit import output
from pre_commit.clientlib import InvalidManifestError
from pre_commit.clientlib import load_config
from pre_commit.clientlib import load_manifest
from pre_commit.clientlib import LOCAL
from pre_commit.clientlib import META
from pre_commit.commands.migrate_config import migrate_config
from pre_commit.store import Store
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b
from pre_commit.yaml import yaml_dump
from pre_commit.yaml import yaml_load


class RevInfo(NamedTuple):
    repo: str
    rev: str
    frozen: str | None

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> RevInfo:
        return cls(config['repo'], config['rev'], None)

    def update(self, tags_only: bool, freeze: bool) -> RevInfo:
        git_cmd = ('git', *git.NO_FS_MONITOR)

        if tags_only:
            tag_cmd = (
                *git_cmd, 'describe',
                'FETCH_HEAD', '--tags', '--abbrev=0',
            )
        else:
            tag_cmd = (
                *git_cmd, 'describe',
                'FETCH_HEAD', '--tags', '--exact',
            )

        with tempfile.TemporaryDirectory() as tmp:
            git.init_repo(tmp, self.repo)
            cmd_output_b(
                *git_cmd, 'fetch', 'origin', 'HEAD', '--tags',
                cwd=tmp,
            )

            try:
                rev = cmd_output(*tag_cmd, cwd=tmp)[1].strip()
            except CalledProcessError:
                cmd = (*git_cmd, 'rev-parse', 'FETCH_HEAD')
                rev = cmd_output(*cmd, cwd=tmp)[1].strip()
            else:
                if tags_only:
                    rev = git.get_best_candidate_tag(rev, tmp)

            frozen = None
            if freeze:
                exact_rev_cmd = (*git_cmd, 'rev-parse', rev)
                exact = cmd_output(*exact_rev_cmd, cwd=tmp)[1].strip()
                if exact != rev:
                    rev, frozen = exact, rev
        return self._replace(rev=rev, frozen=frozen)


class RepositoryCannotBeUpdatedError(RuntimeError):
    pass


def _check_hooks_still_exist_at_rev(
        repo_config: dict[str, Any],
        info: RevInfo,
        store: Store,
) -> None:
    try:
        path = store.clone(repo_config['repo'], info.rev)
        manifest = load_manifest(os.path.join(path, C.MANIFEST_FILE))
    except InvalidManifestError as e:
        raise RepositoryCannotBeUpdatedError(str(e))

    # See if any of our hooks were deleted with the new commits
    hooks = {hook['id'] for hook in repo_config['hooks']}
    hooks_missing = hooks - {hook['id'] for hook in manifest}
    if hooks_missing:
        raise RepositoryCannotBeUpdatedError(
            f'Cannot update because the update target is missing these '
            f'hooks:\n{", ".join(sorted(hooks_missing))}',
        )


REV_LINE_RE = re.compile(r'^(\s+)rev:(\s*)([\'"]?)([^\s#]+)(.*)(\r?\n)$')


def _original_lines(
        path: str,
        rev_infos: list[RevInfo | None],
        retry: bool = False,
) -> tuple[list[str], list[int]]:
    """detect `rev:` lines or reformat the file"""
    with open(path, newline='') as f:
        original = f.read()

    lines = original.splitlines(True)
    idxs = [i for i, line in enumerate(lines) if REV_LINE_RE.match(line)]
    if len(idxs) == len(rev_infos):
        return lines, idxs
    elif retry:
        raise AssertionError('could not find rev lines')
    else:
        with open(path, 'w') as f:
            f.write(yaml_dump(yaml_load(original)))
        return _original_lines(path, rev_infos, retry=True)


def _write_new_config(path: str, rev_infos: list[RevInfo | None]) -> None:
    lines, idxs = _original_lines(path, rev_infos)

    for idx, rev_info in zip(idxs, rev_infos):
        if rev_info is None:
            continue
        match = REV_LINE_RE.match(lines[idx])
        assert match is not None
        new_rev_s = yaml_dump({'rev': rev_info.rev}, default_style=match[3])
        new_rev = new_rev_s.split(':', 1)[1].strip()
        if rev_info.frozen is not None:
            comment = f'  # frozen: {rev_info.frozen}'
        elif match[5].strip().startswith('# frozen:'):
            comment = ''
        else:
            comment = match[5]
        lines[idx] = f'{match[1]}rev:{match[2]}{new_rev}{comment}{match[6]}'

    with open(path, 'w', newline='') as f:
        f.write(''.join(lines))


def autoupdate(
        config_file: str,
        store: Store,
        tags_only: bool,
        freeze: bool,
        repos: Sequence[str] = (),
        jobs: int = 1,
) -> int:
    """Auto-update the pre-commit config to the latest versions of repos."""
    migrate_config(config_file, quiet=True)
    retv = 0
    changed = False

    config = load_config(config_file)
    rev_infos: list[RevInfo | None | object] = [None] * len(config['repos'])
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {}
        for at, repo_config in enumerate(config['repos']):
            future = pool.submit(
                _run_one, repo_config, store, tags_only, freeze, repos,
                jobs != 1,
            )
            futures[future] = at
        for future in as_completed(futures):
            try:
                change, new_info = future.result()
            except RepositoryCannotBeUpdatedError:
                retv = 1
            else:
                changed = changed or change
                rev_infos[futures[future]] = new_info
    if changed:
        info = cast(
            List[Union[RevInfo, None]],
            [i for i in rev_infos if i is not object],
        )
        _write_new_config(config_file, info)

    return retv


def _run_one(
        repo_config: dict[str, str],
        store: Store,
        tags_only: bool,
        freeze: bool,
        repos: Sequence[str] = (),
        parallel: bool = False,
) -> tuple[bool, RevInfo | None | object]:
    if repo_config['repo'] in {LOCAL, META}:
        return False, object

    info = RevInfo.from_config(repo_config)
    if repos and info.repo not in repos:
        return False, None

    pref = f'Updating {info.repo} ... '
    if not parallel:
        output.write(pref)
    new_info = info.update(tags_only=tags_only, freeze=freeze)
    try:
        _check_hooks_still_exist_at_rev(repo_config, new_info, store)
    except RepositoryCannotBeUpdatedError as error:
        output.write_line(f'{pref if parallel else ""}{error.args[0]}')
        raise

    if new_info.rev != info.rev:
        changed = True
        if new_info.frozen:
            updated_to = f'{new_info.frozen} (frozen)'
        else:
            updated_to = new_info.rev
        msg = f'{pref if parallel else ""}updating {info.rev} -> {updated_to}.'
        output.write_line(msg)
    else:
        changed = False
        output.write_line(f'{pref if parallel else ""}already up to date.')
    return changed, new_info
