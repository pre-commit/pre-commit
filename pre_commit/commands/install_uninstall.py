from __future__ import print_function
from __future__ import unicode_literals

import io
import itertools
import logging
import os.path
import shutil
import sys

from pre_commit import git
from pre_commit import output
from pre_commit.clientlib import load_config
from pre_commit.repository import all_hooks
from pre_commit.repository import install_hook_envs
from pre_commit.util import make_executable
from pre_commit.util import mkdirp
from pre_commit.util import resource_text


logger = logging.getLogger(__name__)

# This is used to identify the hook file we install
PRIOR_HASHES = (
    '4d9958c90bc262f47553e2c073f14cfe',
    'd8ee923c46731b42cd95cc869add4062',
    '49fd668cb42069aa1b6048464be5d395',
    '79f09a650522a87b0da915d0d983b2de',
    'e358c9dae00eac5d06b38dfdb1e33a8c',
)
CURRENT_HASH = '138fd403232d2ddd5efb44317e38bf03'
TEMPLATE_START = '# start templated\n'
TEMPLATE_END = '# end templated\n'


def _hook_paths(hook_type, git_dir=None):
    git_dir = git_dir if git_dir is not None else git.get_git_dir()
    pth = os.path.join(git_dir, 'hooks', hook_type)
    return pth, '{}.legacy'.format(pth)


def is_our_script(filename):
    if not os.path.exists(filename):  # pragma: windows no cover (symlink)
        return False
    with io.open(filename) as f:
        contents = f.read()
    return any(h in contents for h in (CURRENT_HASH,) + PRIOR_HASHES)


def shebang():
    if sys.platform == 'win32':
        py = 'python'
    else:
        # Homebrew/homebrew-core#35825: be more timid about appropriate `PATH`
        path_choices = [p for p in os.defpath.split(os.pathsep) if p]
        exe_choices = [
            'python{}'.format('.'.join(str(v) for v in sys.version_info[:i]))
            for i in range(3)
        ]
        for path, exe in itertools.product(path_choices, exe_choices):
            if os.path.exists(os.path.join(path, exe)):
                py = exe
                break
        else:
            py = 'python'
    return '#!/usr/bin/env {}'.format(py)


def _install_hook_script(
        config_file, hook_type,
        overwrite=False, skip_on_missing_config=False, git_dir=None,
):
    hook_path, legacy_path = _hook_paths(hook_type, git_dir=git_dir)

    mkdirp(os.path.dirname(hook_path))

    # If we have an existing hook, move it to pre-commit.legacy
    if os.path.lexists(hook_path) and not is_our_script(hook_path):
        shutil.move(hook_path, legacy_path)

    # If we specify overwrite, we simply delete the legacy file
    if overwrite and os.path.exists(legacy_path):
        os.remove(legacy_path)
    elif os.path.exists(legacy_path):
        output.write_line(
            'Running in migration mode with existing hooks at {}\n'
            'Use -f to use only pre-commit.'.format(legacy_path),
        )

    params = {
        'CONFIG': config_file,
        'HOOK_TYPE': hook_type,
        'INSTALL_PYTHON': sys.executable,
        'SKIP_ON_MISSING_CONFIG': skip_on_missing_config,
    }

    with io.open(hook_path, 'w') as hook_file:
        contents = resource_text('hook-tmpl')
        before, rest = contents.split(TEMPLATE_START)
        to_template, after = rest.split(TEMPLATE_END)

        before = before.replace('#!/usr/bin/env python3', shebang())

        hook_file.write(before + TEMPLATE_START)
        for line in to_template.splitlines():
            var = line.split()[0]
            hook_file.write('{} = {!r}\n'.format(var, params[var]))
        hook_file.write(TEMPLATE_END + after)
    make_executable(hook_path)

    output.write_line('pre-commit installed at {}'.format(hook_path))


def install(
        config_file, store, hook_types,
        overwrite=False, hooks=False,
        skip_on_missing_config=False, git_dir=None,
):
    if git.has_core_hookpaths_set():
        logger.error(
            'Cowardly refusing to install hooks with `core.hooksPath` set.\n'
            'hint: `git config --unset-all core.hooksPath`',
        )
        return 1

    for hook_type in hook_types:
        _install_hook_script(
            config_file, hook_type,
            overwrite=overwrite,
            skip_on_missing_config=skip_on_missing_config,
            git_dir=git_dir,
        )

    if hooks:
        install_hooks(config_file, store)

    return 0


def install_hooks(config_file, store):
    install_hook_envs(all_hooks(load_config(config_file), store), store)


def _uninstall_hook_script(hook_type):  # type: (str) -> None
    hook_path, legacy_path = _hook_paths(hook_type)

    # If our file doesn't exist or it isn't ours, gtfo.
    if not os.path.exists(hook_path) or not is_our_script(hook_path):
        return

    os.remove(hook_path)
    output.write_line('{} uninstalled'.format(hook_type))

    if os.path.exists(legacy_path):
        os.rename(legacy_path, hook_path)
        output.write_line('Restored previous hooks to {}'.format(hook_path))


def uninstall(hook_types):
    for hook_type in hook_types:
        _uninstall_hook_script(hook_type)
    return 0
