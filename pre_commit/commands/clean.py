from __future__ import print_function
from __future__ import unicode_literals

import os.path

from pre_commit import output
from pre_commit.util import rmtree


def clean(store):
    legacy_path = os.path.expanduser('~/.pre-commit')
    for directory in (store.directory, legacy_path):
        if os.path.exists(directory):
            rmtree(directory)
            output.write_line('Cleaned {}.'.format(directory))
    return 0
