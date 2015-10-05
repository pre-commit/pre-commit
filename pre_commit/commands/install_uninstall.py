from __future__ import print_function
from __future__ import unicode_literals

import io
import logging
import os
import os.path
import stat
import sys

from pre_commit.logging_handler import LoggingHandler
from pre_commit.util import resource_filename


logger = logging.getLogger('pre_commit')


# This is used to identify the hook file we install
PREVIOUS_IDENTIFYING_HASHES = (
    '4d9958c90bc262f47553e2c073f14cfe',
    'd8ee923c46731b42cd95cc869add4062',
    '49fd668cb42069aa1b6048464be5d395',
    '79f09a650522a87b0da915d0d983b2de',
)


IDENTIFYING_HASH = 'e358c9dae00eac5d06b38dfdb1e33a8c'


def is_our_pre_commit(filename):
    if not os.path.exists(filename):
        return False
    return IDENTIFYING_HASH in io.open(filename).read()


def is_previous_pre_commit(filename):
    if not os.path.exists(filename):
        return False
    contents = io.open(filename).read()
    return any(hash in contents for hash in PREVIOUS_IDENTIFYING_HASHES)


def make_executable(filename):
    original_mode = os.stat(filename).st_mode
    os.chmod(
        filename,
        original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )


def install(runner, overwrite=False, hooks=False, hook_type='pre-commit'):
    """Install the pre-commit hooks."""
    hook_path = runner.get_hook_path(hook_type)
    legacy_path = hook_path + '.legacy'

    if not os.path.exists(os.path.dirname(hook_path)):
        os.makedirs(os.path.dirname(hook_path))

    # If we have an existing hook, move it to pre-commit.legacy
    if (
        os.path.lexists(hook_path) and
        not is_our_pre_commit(hook_path) and
        not is_previous_pre_commit(hook_path)
    ):
        os.rename(hook_path, legacy_path)

    # If we specify overwrite, we simply delete the legacy file
    if overwrite and os.path.exists(legacy_path):
        os.remove(legacy_path)
    elif os.path.exists(legacy_path):
        print(
            'Running in migration mode with existing hooks at {0}\n'
            'Use -f to use only pre-commit.'.format(
                legacy_path,
            )
        )

    with io.open(hook_path, 'w') as pre_commit_file_obj:
        if hook_type == 'pre-push':
            with io.open(resource_filename('pre-push-tmpl')) as fp:
                pre_push_contents = fp.read()
        else:
            pre_push_contents = ''

        contents = io.open(resource_filename('hook-tmpl')).read().format(
            sys_executable=sys.executable,
            hook_type=hook_type,
            pre_push=pre_push_contents,
        )
        pre_commit_file_obj.write(contents)
    make_executable(hook_path)

    print('pre-commit installed at {0}'.format(hook_path))

    # If they requested we install all of the hooks, do so.
    if hooks:
        # Set up our logging handler
        logger.addHandler(LoggingHandler(False))
        logger.setLevel(logging.INFO)
        for repository in runner.repositories:
            repository.require_installed()

    return 0


def uninstall(runner, hook_type='pre-commit'):
    """Uninstall the pre-commit hooks."""
    hook_path = runner.get_hook_path(hook_type)
    legacy_path = hook_path + '.legacy'
    # If our file doesn't exist or it isn't ours, gtfo.
    if (
        not os.path.exists(hook_path) or (
            not is_our_pre_commit(hook_path) and
            not is_previous_pre_commit(hook_path)
        )
    ):
        return 0

    os.remove(hook_path)
    print('{0} uninstalled'.format(hook_type))

    if os.path.exists(legacy_path):
        os.rename(legacy_path, hook_path)
        print('Restored previous hooks to {0}'.format(hook_path))

    return 0
