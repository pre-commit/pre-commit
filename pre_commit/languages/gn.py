from __future__ import annotations

import contextlib
import functools
import os.path
import platform
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Generator
from collections.abc import Sequence
from typing import ContextManager
from typing import IO

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.prefix import Prefix
from pre_commit.util import make_executable

ENVIRONMENT_DIR = 'gn_env'
health_check = lang_base.basic_health_check
run_hook = lang_base.basic_run_hook

_ARCH_ALIASES = {
    'x86_64': 'amd64',
    'aarch64': 'arm64',
    'armv8': 'arm64',
}
_ARCH = platform.machine().lower()
_ARCH = _ARCH_ALIASES.get(_ARCH, _ARCH)


def _open_archive(bio: IO[bytes]) -> ContextManager[zipfile.ZipFile]:
    return zipfile.ZipFile(bio)


def _get_gn_url() -> str:
    os_name = platform.system().lower()
    if os_name == 'linux':
        os_name = 'linux-' + _ARCH
    elif os_name == 'darwin':
        os_name = 'mac-' + _ARCH
    elif os_name == 'windows':
        os_name = 'windows-' + _ARCH
    return 'https://chrome-infra-packages.appspot.com/dl/gn/gn/' + \
        f'{os_name}/+/latest'


def _install_gn(dest: str) -> None:
    try:
        resp = urllib.request.urlopen(_get_gn_url())
    except urllib.error.HTTPError as e:  # pragma: no cover
        os_name = platform.system().lower()
        raise ValueError(
            f'Could not find GN for your system (os={os_name}; arch={_ARCH})',
        ) from e
    else:
        with tempfile.TemporaryFile() as f:
            shutil.copyfileobj(resp, f)
            f.seek(0)
            with _open_archive(f) as archive:
                archive.extractall(dest)
                make_executable(f'{dest}/gn')


@functools.lru_cache(maxsize=1)
def get_default_version() -> str:
    if lang_base.exe_exists('gn'):
        return 'system'
    else:
        return C.DEFAULT


def get_env_patch(venv: str, version: str) -> PatchesT:
    if version == 'system':
        return ()

    return (('PATH', (venv, os.pathsep, Var('PATH'))),)


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    env_dir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(env_dir, version)):
        yield


def install_environment(
    prefix: Prefix,
    version: str,
    additional_dependencies: Sequence[str],
) -> None:
    if version == 'system':
        return
    env_dir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    _install_gn(env_dir)
