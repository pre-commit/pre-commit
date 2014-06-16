from __future__ import print_function
from __future__ import unicode_literals

import io
import os
import os.path
import pkg_resources
import stat

# This is used to identify the hook file we install
IDENTIFYING_HASH = 'd8ee923c46731b42cd95cc869add4062'


def is_our_pre_commit(filename):
    return IDENTIFYING_HASH in io.open(filename).read()


def make_executable(filename):
    original_mode = os.stat(filename).st_mode
    os.chmod(
        filename,
        original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )


def install(runner):
    """Install the pre-commit hooks."""
    pre_commit_file = pkg_resources.resource_filename(
        'pre_commit', 'resources/pre-commit-hook',
    )

    # If we have an existing hook, move it to pre-commit.legacy
    if (
        os.path.exists(runner.pre_commit_path) and
        not is_our_pre_commit(runner.pre_commit_path)
    ):
        os.rename(runner.pre_commit_path, runner.pre_commit_path + '.legacy')

    with open(runner.pre_commit_path, 'w') as pre_commit_file_obj:
        pre_commit_file_obj.write(open(pre_commit_file).read())
    make_executable(runner.pre_commit_path)

    print('pre-commit installed at {0}'.format(runner.pre_commit_path))
    return 0
