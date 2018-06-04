# -*- coding: utf-8 -*-
from __future__ import print_function
from __future__ import unicode_literals

import sys


def main():
    # Intentionally write mixed encoding to the output.  This should not crash
    # pre-commit and should write bytes to the output.
    sys.stdout.buffer.write('☃'.encode('UTF-8') + '²'.encode('latin1') + b'\n')
    # Return 1 to trigger printing
    return 1
