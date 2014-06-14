from __future__ import print_function
from __future__ import unicode_literals

import os.path
import shutil


def clean(runner):
    if os.path.exists(runner.store.directory):
        shutil.rmtree(runner.store.directory)
        print('Cleaned {0}.'.format(runner.store.directory))
    return 0
