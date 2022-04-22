from __future__ import annotations

import argparse
import logging
import os
import shlex
from typing import Any
from typing import NamedTuple
from typing import Sequence

from pre_commit.prefix import Prefix

logger = logging.getLogger('pre_commit')


class Hook(NamedTuple):
    src: str
    prefix: Prefix
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
    def cmd(self) -> tuple[str, ...]:
        return (*shlex.split(self.entry), *self.args)

    @property
    def install_key(self) -> tuple[Prefix, str, str, tuple[str, ...]]:
        return (
            self.prefix,
            self.language,
            self.language_version,
            tuple(self.additional_dependencies),
        )

    @classmethod
    def create(cls, src: str, prefix: Prefix, dct: dict[str, Any]) -> Hook:
        # TODO: have cfgv do this (?)
        extra_keys = set(dct) - _KEYS
        if extra_keys:
            logger.warning(
                f'Unexpected key(s) present on {src} => {dct["id"]}: '
                f'{", ".join(sorted(extra_keys))}',
            )
        return cls(src=src, prefix=prefix, **{k: dct[k] for k in _KEYS})

    def expand(self, args: argparse.Namespace, config_file: str) -> Hook:
        map_ = {
            '%CONFIG_BASEPATH%': os.path.dirname(os.path.abspath(config_file)),
        }
        values = self._asdict()
        for k, v in map_.items():
            values['entry'] = values['entry'].replace(k, v)
            values['args'] = [x.replace(k, v) for x in values['args']]
        return Hook(**values)


_KEYS = frozenset(set(Hook._fields) - {'src', 'prefix'})
