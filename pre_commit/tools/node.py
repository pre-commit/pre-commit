from __future__ import annotations

import functools
import json

from pre_commit.prefix import Prefix
from pre_commit.request import fetch

RESOLVABLE = ('latest', 'lts')


@functools.cache
def _node_versions() -> dict[str, str]:
    resp = fetch('https://nodejs.org/download/release/index.json')
    contents = json.load(resp)

    ret = {'latest': contents[0]['version']}
    for dct in contents:
        if dct['lts']:
            ret['lts'] = dct['version']
            break
    else:
        raise AssertionError('unreachable')

    return ret


def resolve(version: str) -> str:
    return _node_versions()[version]


@functools.cache
def _target_platform() -> str:
    # to support:
    # linux-arm64, linux-ppc64le, linux-s390x, linux-x64
    # osx-arm64-tar, osx-x86-tar
    # win-arm64-zip, win-x64-zip
    # or fallback to `src` ?
    raise NotImplementedError


def install(prefix: Prefix, version: str) -> None:
    # TODO: download and extract to prefix
    raise NotImplementedError


def health_check(prefix: Prefix, version: str) -> str | None:
    # TODO: previously checked `node --version`
    # TODO: but maybe just check that the installed os/arch is correct?
    return None
