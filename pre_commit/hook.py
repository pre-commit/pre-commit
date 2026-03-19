from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any
from typing import NamedTuple

logger = logging.getLogger('pre_commit')


class InstallKey(NamedTuple):
    repo: str
    rev: str
    language: str
    language_version: str
    additional_dependencies: tuple[str, ...]

    def keystr(self) -> str:
        return json.dumps(self, separators=(',', ':'))


class Hook(NamedTuple):
    repo: str
    rev: str
    id: str
    name: str
    entry: str
    language: str
    alias: str
    files: str
    exclude: str
    types: Sequence[str]
    types_or: Sequence[str]
    exclude_types: Sequence[str]
    additional_dependencies: Sequence[str]
    args: Sequence[str]
    always_run: bool
    fail_fast: bool
    pass_filenames: bool
    description: str
    language_version: str
    log_file: str
    minimum_pre_commit_version: str
    require_serial: bool
    stages: Sequence[str]
    verbose: bool

    @property
    def install_key(self) -> InstallKey:
        return InstallKey(
            repo=self.repo,
            rev=self.rev,
            language=self.language,
            language_version=self.language_version,
            additional_dependencies=tuple(self.additional_dependencies),
        )

    @classmethod
    def create(cls, repo: str, rev: str, dct: dict[str, Any]) -> Hook:
        # TODO: have cfgv do this (?)
        extra_keys = set(dct) - _KEYS
        if extra_keys:
            logger.warning(
                f'Unexpected key(s) present on {repo} => {dct["id"]}: '
                f'{", ".join(sorted(extra_keys))}',
            )
        return cls(repo=repo, rev=rev, **{k: dct[k] for k in _KEYS})


_KEYS = frozenset(set(Hook._fields) - {'repo', 'rev'})
