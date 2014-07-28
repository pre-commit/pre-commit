from __future__ import print_function
from __future__ import unicode_literals

import io
import logging
import os
import os.path
import stat

from pre_commit.logging_handler import LoggingHandler
from pre_commit.util import resource_filename


logger = logging.getLogger('pre_commit')


# This is used to identify the hook file we install
PREVIOUS_IDENTIFYING_HASHES = [
    'd8ee923c46731b42cd95cc869add4062',
]


IDENTIFYING_HASH = '4d9958c90bc262f47553e2c073f14cfe'


def is_our_pre_commit(filename):
    return IDENTIFYING_HASH in io.open(filename).read()


def is_previous_pre_commit(filename):
    contents = io.open(filename).read()
    return any(hash in contents for hash in PREVIOUS_IDENTIFYING_HASHES)


def make_executable(filename):
    original_mode = os.stat(filename).st_mode
    os.chmod(
        filename,
        original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )


def install(runner, overwrite=False, hooks=False):
    """Install the pre-commit hooks."""
    pre_commit_file = resource_filename('pre-commit-hook')

    # If we have an existing hook, move it to pre-commit.legacy
    if (
        os.path.exists(runner.pre_commit_path) and
        not is_our_pre_commit(runner.pre_commit_path) and
        not is_previous_pre_commit(runner.pre_commit_path)
    ):
        os.rename(runner.pre_commit_path, runner.pre_commit_legacy_path)

    # If we specify overwrite, we simply delete the legacy file
    if overwrite and os.path.exists(runner.pre_commit_legacy_path):
        os.remove(runner.pre_commit_legacy_path)
    elif os.path.exists(runner.pre_commit_legacy_path):
        print(
            'Running in migration mode with existing hooks at {0}\n'
            'Use -f to use only pre-commit.'.format(
                runner.pre_commit_legacy_path,
            )
        )

    with open(runner.pre_commit_path, 'w') as pre_commit_file_obj:
        pre_commit_file_obj.write(open(pre_commit_file).read())
    make_executable(runner.pre_commit_path)

    print('pre-commit installed at {0}'.format(runner.pre_commit_path))

    # If they requested we install all of the hooks, do so.
    if hooks:
        # Set up our logging handler
        logger.addHandler(LoggingHandler(False))
        logger.setLevel(logging.INFO)
        for repository in runner.repositories:
            repository.require_installed()

    return 0


def uninstall(runner):
    """Uninstall the pre-commit hooks."""
    # If our file doesn't exist or it isn't ours, gtfo.
    if (
        not os.path.exists(runner.pre_commit_path) or (
            not is_our_pre_commit(runner.pre_commit_path) and
            not is_previous_pre_commit(runner.pre_commit_path)
        )
    ):
        return 0

    os.remove(runner.pre_commit_path)
    print('pre-commit uninstalled')

    if os.path.exists(runner.pre_commit_legacy_path):
        os.rename(runner.pre_commit_legacy_path, runner.pre_commit_path)
        print('Restored previous hooks to {0}'.format(runner.pre_commit_path))

    return 0
