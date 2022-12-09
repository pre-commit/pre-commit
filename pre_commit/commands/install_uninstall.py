from __future__ import annotations

import logging
import os.path
import shlex
import shutil
import sys

from pre_commit import git
from pre_commit import output
from pre_commit.clientlib import InvalidConfigError
from pre_commit.clientlib import load_config
from pre_commit.repository import all_hooks
from pre_commit.repository import install_hook_envs
from pre_commit.store import Store
from pre_commit.util import make_executable
from pre_commit.util import resource_text

logger = logging.getLogger(__name__)

# This is used to identify the hook file we install
PRIOR_HASHES = (
    b'4d9958c90bc262f47553e2c073f14cfe',
    b'd8ee923c46731b42cd95cc869add4062',
    b'49fd668cb42069aa1b6048464be5d395',
    b'79f09a650522a87b0da915d0d983b2de',
    b'e358c9dae00eac5d06b38dfdb1e33a8c',
)
CURRENT_HASH = b'138fd403232d2ddd5efb44317e38bf03'
TEMPLATE_START = '# start templated\n'
TEMPLATE_END = '# end templated\n'


def _hook_types(cfg_filename: str, hook_types: list[str] | None) -> list[str]:
    if hook_types is not None:
        return hook_types
    else:
        try:
            cfg = load_config(cfg_filename)
        except InvalidConfigError:
            return ['pre-commit']
        else:
            return cfg['default_install_hook_types']


def _hook_paths(
        hook_type: str,
        git_dir: str | None = None,
) -> tuple[str, str]:
    git_dir = git_dir if git_dir is not None else git.get_git_common_dir()
    pth = os.path.join(git_dir, 'hooks', hook_type)
    return pth, f'{pth}.legacy'


def is_our_script(filename: str) -> bool:
    if not os.path.exists(filename):  # pragma: win32 no cover (symlink)
        return False
    with open(filename, 'rb') as f:
        contents = f.read()
    return any(h in contents for h in (CURRENT_HASH,) + PRIOR_HASHES)


def _install_hook_script(
        config_file: str,
        hook_type: str,
        overwrite: bool = False,
        skip_on_missing_config: bool = False,
        git_dir: str | None = None,
) -> None:
    hook_path, legacy_path = _hook_paths(hook_type, git_dir=git_dir)

    os.makedirs(os.path.dirname(hook_path), exist_ok=True)

    # If we have an existing hook, move it to pre-commit.legacy
    if os.path.lexists(hook_path) and not is_our_script(hook_path):
        shutil.move(hook_path, legacy_path)

    # If we specify overwrite, we simply delete the legacy file
    if overwrite and os.path.exists(legacy_path):
        os.remove(legacy_path)
    elif os.path.exists(legacy_path):
        output.write_line(
            f'Running in migration mode with existing hooks at {legacy_path}\n'
            f'Use -f to use only pre-commit.',
        )

    args = ['hook-impl', f'--config={config_file}', f'--hook-type={hook_type}']
    if skip_on_missing_config:
        args.append('--skip-on-missing-config')

    with open(hook_path, 'w') as hook_file:
        contents = resource_text('hook-tmpl')
        before, rest = contents.split(TEMPLATE_START)
        _, after = rest.split(TEMPLATE_END)

        # on windows always use `/bin/sh` since `bash` might not be on PATH
        # though we use bash-specific features `sh` on windows is actually
        # bash in "POSIXLY_CORRECT" mode which still supports the features we
        # use: subshells / arrays
        if sys.platform == 'win32':  # pragma: win32 cover
            hook_file.write('#!/bin/sh\n')

        hook_file.write(before + TEMPLATE_START)
        hook_file.write(f'INSTALL_PYTHON={shlex.quote(sys.executable)}\n')
        # TODO: python3.8+: shlex.join
        args_s = ' '.join(shlex.quote(part) for part in args)
        hook_file.write(f'ARGS=({args_s})\n')
        hook_file.write(TEMPLATE_END + after)
    make_executable(hook_path)

    output.write_line(f'pre-commit installed at {hook_path}')


def install(
        config_file: str,
        store: Store,
        hook_types: list[str] | None,
        overwrite: bool = False,
        hooks: bool = False,
        skip_on_missing_config: bool = False,
        git_dir: str | None = None,
) -> int:
    if git_dir is None and git.has_core_hookpaths_set():
        logger.error(
            'Cowardly refusing to install hooks with `core.hooksPath` set.\n'
            'hint: `git config --unset-all core.hooksPath`',
        )
        return 1

    for hook_type in _hook_types(config_file, hook_types):
        _install_hook_script(
            config_file, hook_type,
            overwrite=overwrite,
            skip_on_missing_config=skip_on_missing_config,
            git_dir=git_dir,
        )

    if hooks:
        install_hooks(config_file, store)

    return 0


def install_hooks(config_file: str, store: Store) -> int:
    install_hook_envs(all_hooks(load_config(config_file), store), store)
    return 0


def _uninstall_hook_script(hook_type: str) -> None:
    hook_path, legacy_path = _hook_paths(hook_type)

    # If our file doesn't exist or it isn't ours, gtfo.
    if not os.path.exists(hook_path) or not is_our_script(hook_path):
        return

    os.remove(hook_path)
    output.write_line(f'{hook_type} uninstalled')

    if os.path.exists(legacy_path):
        os.replace(legacy_path, hook_path)
        output.write_line(f'Restored previous hooks to {hook_path}')


def uninstall(config_file: str, hook_types: list[str] | None) -> int:
    for hook_type in _hook_types(config_file, hook_types):
        _uninstall_hook_script(hook_type)
    return 0
