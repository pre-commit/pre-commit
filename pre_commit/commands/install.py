from __future__ import print_function
from __future__ import unicode_literals

import os
import pkg_resources
import stat


def install(runner):
    """Install the pre-commit hooks."""
    pre_commit_file = pkg_resources.resource_filename(
        'pre_commit', 'resources/pre-commit.sh',
    )
    with open(runner.pre_commit_path, 'w') as pre_commit_file_obj:
        pre_commit_file_obj.write(open(pre_commit_file).read())

    original_mode = os.stat(runner.pre_commit_path).st_mode
    os.chmod(
        runner.pre_commit_path,
        original_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
    )

    print('pre-commit installed at {0}'.format(runner.pre_commit_path))
    return 0
