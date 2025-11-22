from __future__ import annotations

import contextlib
import functools
import os.path
import platform
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Generator
from collections.abc import Sequence

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.languages.python import bin_dir
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'bunenv'
run_hook = lang_base.basic_run_hook

# Architecture mapping for Bun binary downloads
_ARCH_ALIASES = {
    'x86_64': 'x64',
    'amd64': 'x64',
    'aarch64': 'aarch64',
    'arm64': 'aarch64',
}
_ARCH = platform.machine().lower()
_ARCH = _ARCH_ALIASES.get(_ARCH, _ARCH)


@functools.lru_cache(maxsize=1)
def get_default_version() -> str:
    """Detect if Bun is installed system-wide."""
    # Check for system-installed bun
    if lang_base.exe_exists('bun'):
        return 'system'
    else:
        return C.DEFAULT


def _get_platform() -> str:
    """Get platform string for Bun binary downloads."""
    if sys.platform == 'darwin':
        return 'darwin'
    elif sys.platform == 'win32':
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    else:
        raise AssertionError(f'Unsupported platform: {sys.platform}')


def _normalize_version(version: str) -> str:
    """Normalize version string for download URL."""
    if version == C.DEFAULT:
        return 'latest'
    # Ensure version has 'bun-v' prefix for download URL
    if not version.startswith('bun-v'):
        if version.startswith('v'):
            return f'bun-{version}'
        else:
            return f'bun-v{version}'
    return version


def _get_download_url(version: str) -> str:
    """Construct Bun binary download URL from GitHub releases."""
    platform_name = _get_platform()
    normalized_version = _normalize_version(version)

    # Bun release URL format:
    # https://github.com/oven-sh/bun/releases/download/bun-v1.1.42/bun-darwin-x64.zip
    # https://github.com/oven-sh/bun/releases/download/bun-v1.1.42/bun-linux-x64.zip
    # https://github.com/oven-sh/bun/releases/download/bun-v1.1.42/bun-windows-x64.zip
    base_url = 'https://github.com/oven-sh/bun/releases'

    if normalized_version == 'latest':
        # Use latest release
        return f'{base_url}/latest/download/bun-{platform_name}-{_ARCH}.zip'
    else:
        # Use specific version
        return (
            f'{base_url}/download/{normalized_version}/'
            f'bun-{platform_name}-{_ARCH}.zip'
        )


def _install_bun(version: str, dest: str) -> None:
    """Download and extract Bun binary to destination directory."""
    url = _get_download_url(version)

    try:
        resp = urllib.request.urlopen(url)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(
                f'Could not find Bun version matching your requirements '
                f'(version={version}; os={_get_platform()}; '
                f'arch={_ARCH}). Check available versions at '
                f'https://github.com/oven-sh/bun/releases',
            ) from e
        else:
            raise

    with tempfile.TemporaryFile() as f:
        shutil.copyfileobj(resp, f)
        f.seek(0)

        with zipfile.ZipFile(f) as zipf:
            zipf.extractall(dest)

    # Bun zipfile contains a directory like 'bun-darwin-x64' or 'bun-linux-x64'
    # Move the binary from the extracted directory to dest/bin/
    bin_dir_path = os.path.join(dest, 'bin')
    os.makedirs(bin_dir_path, exist_ok=True)

    # Find the extracted directory
    for item in os.listdir(dest):
        item_path = os.path.join(dest, item)
        if os.path.isdir(item_path) and item.startswith('bun-'):
            # Move bun executable to bin directory
            bun_exe = 'bun.exe' if sys.platform == 'win32' else 'bun'
            src_exe = os.path.join(item_path, bun_exe)
            if os.path.exists(src_exe):
                shutil.move(src_exe, os.path.join(bin_dir_path, bun_exe))
            # Remove the extracted directory
            shutil.rmtree(item_path)
            break


def get_env_patch(venv: str) -> PatchesT:
    """Prepare environment variables for Bun execution."""
    # Bun is much simpler than Node - primarily just needs PATH
    return (
        ('PATH', (bin_dir(venv), os.pathsep, Var('PATH'))),
        # BUN_INSTALL controls where global packages are installed
        ('BUN_INSTALL', venv),
    )


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None]:
    """Context manager for Bun environment."""
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir)):
        yield


def health_check(prefix: Prefix, version: str) -> str | None:
    """Check if Bun environment is healthy."""
    with in_env(prefix, version):
        retcode, _, _ = cmd_output_b('bun', '--version', check=False)
        if retcode != 0:  # pragma: no cover
            return f'`bun --version` returned {retcode}'
        else:
            return None


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    """Install Bun environment and dependencies."""
    assert prefix.exists('package.json')
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)

    # Install Bun binary (unless using system version)
    if version != 'system':
        _install_bun(version, envdir)

    with in_env(prefix, version):
        # Install local dependencies from package.json
        # Use --no-progress to avoid cluttering output
        install_cmd = ('bun', 'install', '--no-progress')
        lang_base.setup_cmd(prefix, install_cmd)

        # Install the package globally from the current directory
        # Bun's global install uses `bun add -g` with file: protocol
        # We need to install from an absolute file path, so we use file:.
        # Note: Unlike npm, bun creates symlinks to the local package,
        # so we must NOT delete node_modules or the bin directory.
        abs_prefix = os.path.abspath(prefix.prefix_dir)
        install = ['bun', 'add', '-g', f'file:{abs_prefix}']
        if additional_dependencies:
            install.extend(additional_dependencies)
        lang_base.setup_cmd(prefix, tuple(install))
