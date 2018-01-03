from __future__ import print_function

import sys


def func():
    print(sys.version_info[0])
    print(repr(sys.argv[1:]))
    print('Hello World')
    return 0
