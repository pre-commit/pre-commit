import itertools
import logging
import os.path
import shutil
import sys
from typing import Optional
from typing import Sequence
from typing import Tuple

from pre_commit import git
from pre_commit import output
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
# Homebrew/homebrew-core#35825: be more timid about appropriate `PATH`
# #1312 os.defpath is too restrictive on BSD
POSIX_SEARCH_PATH = ('/usr/local/bin', '/usr/bin', '/bin')
SYS_EXE = os.path.basename(os.path.realpath(sys.executable))


def _hook_paths(
        hook_type: str,
        git_dir: Optional[str] = None,
        core_hookspath: str = '',
) -> Tuple[str, str]:
    if core_hookspath:
        pth = os.path.join(core_hookspath, hook_type)

    else:
        git_dir = git_dir if git_dir is not None else git.get_git_dir()
        pth = os.path.join(git_dir, 'hooks', hook_type)

    return pth, f'{pth}.legacy'


def is_our_script(filename: str) -> bool:
    if not os.path.exists(filename):  # pragma: win32 no cover (symlink)
        return False
    with open(filename, 'rb') as f:
        contents = f.read()
    return any(h in contents for h in (CURRENT_HASH,) + PRIOR_HASHES)


def shebang() -> str:
    if sys.platform == 'win32':
        py, _ = os.path.splitext(SYS_EXE)
    else:
        exe_choices = [
            f'python{sys.version_info[0]}.{sys.version_info[1]}',
            f'python{sys.version_info[0]}',
        ]
        # avoid searching for bare `python` as it's likely to be python 2
        if SYS_EXE != 'python':
            exe_choices.append(SYS_EXE)
        for path, exe in itertools.product(POSIX_SEARCH_PATH, exe_choices):
            if os.access(os.path.join(path, exe), os.X_OK):
                py = exe
                break
        else:
            py = SYS_EXE
    return f'#!/usr/bin/env {py}'


def _install_hook_script(
        config_file: str,
        hook_type: str,
        overwrite: bool = False,
        skip_on_missing_config: bool = False,
        git_dir: Optional[str] = None,
        core_hookspath: str = '',
) -> None:
    hook_path, legacy_path = _hook_paths(
        hook_type,
        git_dir=git_dir,
        core_hookspath=core_hookspath,
    )

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
    params = {'INSTALL_PYTHON': sys.executable, 'ARGS': args}

    with open(hook_path, 'w') as hook_file:
        contents = resource_text('hook-tmpl')
        before, rest = contents.split(TEMPLATE_START)
        to_template, after = rest.split(TEMPLATE_END)

        before = before.replace('#!/usr/bin/env python3', shebang())

        hook_file.write(before + TEMPLATE_START)
        for line in to_template.splitlines():
            var = line.split()[0]
            hook_file.write(f'{var} = {params[var]!r}\n')
        hook_file.write(TEMPLATE_END + after)
    make_executable(hook_path)

    output.write_line(f'pre-commit installed at {hook_path}')


def install(
        config_file: str,
        store: Store,
        hook_types: Sequence[str],
        overwrite: bool = False,
        hooks: bool = False,
        skip_on_missing_config: bool = False,
        follow_hooks_path: bool = False,
        git_dir: Optional[str] = None,
) -> int:
    core_hookspaths_set, core_hookspath = \
        git.has_core_hookpaths_set()
    if git_dir is None and core_hookspaths_set:
        if not follow_hooks_path:
            logger.error(
                'Cowardly refusing to install hooks with `core.hooksPath` set.'
                '\nhint: `git config --unset-all core.hooksPath`, '
                'or use the `--follow-custom-hooks-path` flag',
            )
            return 1

    for hook_type in hook_types:
        _install_hook_script(
            config_file, hook_type,
            overwrite=overwrite,
            skip_on_missing_config=skip_on_missing_config,
            git_dir=git_dir,
            core_hookspath=core_hookspath,
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


def uninstall(hook_types: Sequence[str]) -> int:
    for hook_type in hook_types:
        _uninstall_hook_script(hook_type)
    return 0
