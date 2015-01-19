from __future__ import print_function
from __future__ import unicode_literals

import os.path

from pre_commit.util import rmtree


def clean(runner):
    if os.path.exists(runner.store.directory):
        rmtree(runner.store.directory)
        print('Cleaned {0}.'.format(runner.store.directory))
    return 0
