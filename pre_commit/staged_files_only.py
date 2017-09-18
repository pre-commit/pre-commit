from __future__ import unicode_literals

import contextlib
import io
import logging
import os.path
import time

from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output
from pre_commit.util import mkdirp


logger = logging.getLogger('pre_commit')


def _git_apply(patch):
    args = ('apply', '--whitespace=nowarn', patch)
    try:
        cmd_output('git', *args, encoding=None)
    except CalledProcessError:
        # Retry with autocrlf=false -- see #570
        cmd_output('git', '-c', 'core.autocrlf=false', *args, encoding=None)


@contextlib.contextmanager
def staged_files_only(patch_dir):
    """Clear any unstaged changes from the git working directory inside this
    context.
    """
    # Determine if there are unstaged files
    tree = cmd_output('git', 'write-tree')[1].strip()
    retcode, diff_stdout_binary, _ = cmd_output(
        'git', 'diff-index', '--ignore-submodules', '--binary',
        '--exit-code', '--no-color', '--no-ext-diff', tree, '--',
        retcode=None,
        encoding=None,
    )
    if retcode and diff_stdout_binary.strip():
        patch_filename = 'patch{}'.format(int(time.time()))
        patch_filename = os.path.join(patch_dir, patch_filename)
        logger.warning('Unstaged files detected.')
        logger.info(
            'Stashing unstaged files to {}.'.format(patch_filename),
        )
        # Save the current unstaged changes as a patch
        mkdirp(patch_dir)
        with io.open(patch_filename, 'wb') as patch_file:
            patch_file.write(diff_stdout_binary)

        # Clear the working directory of unstaged changes
        cmd_output('git', 'checkout', '--', '.')
        try:
            yield
        finally:
            # Try to apply the patch we saved
            try:
                _git_apply(patch_filename)
            except CalledProcessError:
                logger.warning(
                    'Stashed changes conflicted with hook auto-fixes... '
                    'Rolling back fixes...',
                )
                # We failed to apply the patch, presumably due to fixes made
                # by hooks.
                # Roll back the changes made by hooks.
                cmd_output('git', 'checkout', '--', '.')
                _git_apply(patch_filename)
            logger.info('Restored changes from {}.'.format(patch_filename))
    else:
        # There weren't any staged files so we don't need to do anything
        # special
        yield
