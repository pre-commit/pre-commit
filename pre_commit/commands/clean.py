from __future__ import print_function
from __future__ import unicode_literals

import os.path

from pre_commit import output
from pre_commit.util import rmtree


def clean(runner):
    if os.path.exists(runner.store.directory):
        rmtree(runner.store.directory)
        output.write_line('Cleaned {}.'.format(runner.store.directory))
    return 0
