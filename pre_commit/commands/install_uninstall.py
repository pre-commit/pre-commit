from __future__ import print_function
from __future__ import unicode_literals

import io
import os.path
import sys

from pre_commit import output
from pre_commit.util import make_executable
from pre_commit.util import mkdirp
from pre_commit.util import resource_filename


# This is used to identify the hook file we install
PRIOR_HASHES = (
    '4d9958c90bc262f47553e2c073f14cfe',
    'd8ee923c46731b42cd95cc869add4062',
    '49fd668cb42069aa1b6048464be5d395',
    '79f09a650522a87b0da915d0d983b2de',
    'e358c9dae00eac5d06b38dfdb1e33a8c',
)
CURRENT_HASH = '138fd403232d2ddd5efb44317e38bf03'


def is_our_script(filename):
    if not os.path.exists(filename):
        return False
    contents = io.open(filename).read()
    return any(h in contents for h in (CURRENT_HASH,) + PRIOR_HASHES)


def install(
        runner, overwrite=False, hooks=False, hook_type='pre-commit',
        skip_on_missing_conf=False,
):
    """Install the pre-commit hooks."""
    hook_path = runner.get_hook_path(hook_type)
    legacy_path = hook_path + '.legacy'

    mkdirp(os.path.dirname(hook_path))

    # If we have an existing hook, move it to pre-commit.legacy
    if os.path.lexists(hook_path) and not is_our_script(hook_path):
        os.rename(hook_path, legacy_path)

    # If we specify overwrite, we simply delete the legacy file
    if overwrite and os.path.exists(legacy_path):
        os.remove(legacy_path)
    elif os.path.exists(legacy_path):
        output.write_line(
            'Running in migration mode with existing hooks at {}\n'
            'Use -f to use only pre-commit.'.format(
                legacy_path,
            ),
        )

    with io.open(hook_path, 'w') as pre_commit_file_obj:
        if hook_type == 'pre-push':
            with io.open(resource_filename('pre-push-tmpl')) as fp:
                pre_push_contents = fp.read()
        else:
            pre_push_contents = ''

        skip_on_missing_conf = 'true' if skip_on_missing_conf else 'false'
        contents = io.open(resource_filename('hook-tmpl')).read().format(
            sys_executable=sys.executable,
            hook_type=hook_type,
            pre_push=pre_push_contents,
            skip_on_missing_conf=skip_on_missing_conf,
        )
        pre_commit_file_obj.write(contents)
    make_executable(hook_path)

    output.write_line('pre-commit installed at {}'.format(hook_path))

    # If they requested we install all of the hooks, do so.
    if hooks:
        install_hooks(runner)

    return 0


def install_hooks(runner):
    for repository in runner.repositories:
        repository.require_installed()


def uninstall(runner, hook_type='pre-commit'):
    """Uninstall the pre-commit hooks."""
    hook_path = runner.get_hook_path(hook_type)
    legacy_path = hook_path + '.legacy'
    # If our file doesn't exist or it isn't ours, gtfo.
    if not os.path.exists(hook_path) or not is_our_script(hook_path):
        return 0

    os.remove(hook_path)
    output.write_line('{} uninstalled'.format(hook_type))

    if os.path.exists(legacy_path):
        os.rename(legacy_path, hook_path)
        output.write_line('Restored previous hooks to {}'.format(hook_path))

    return 0
