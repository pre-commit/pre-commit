from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import os.path
import sys
import traceback

import six

import pre_commit.constants as C
from pre_commit import five
from pre_commit import output
from pre_commit.store import Store


class FatalError(RuntimeError):
    pass


def _to_bytes(exc):
    try:
        return bytes(exc)
    except Exception:
        return six.text_type(exc).encode('UTF-8')


def _log_and_exit(msg, exc, formatted):
    error_msg = b''.join((
        five.to_bytes(msg), b': ',
        five.to_bytes(type(exc).__name__), b': ',
        _to_bytes(exc),
    ))
    output.write_line(error_msg)
    store = Store()
    log_path = os.path.join(store.directory, 'pre-commit.log')
    output.write_line('Check the log at {}'.format(log_path))

    with open(log_path, 'wb') as log:
        def _log_line(*s):  # type: (*str) -> None
            output.write_line(*s, stream=log)

        _log_line('### version information')
        _log_line()
        _log_line('```')
        _log_line('pre-commit version: {}'.format(C.VERSION))
        _log_line('sys.version:')
        for line in sys.version.splitlines():
            _log_line('    {}'.format(line))
        _log_line('sys.executable: {}'.format(sys.executable))
        _log_line('os.name: {}'.format(os.name))
        _log_line('sys.platform: {}'.format(sys.platform))
        _log_line('```')
        _log_line()

        _log_line('### error information')
        _log_line()
        _log_line('```')
        _log_line(error_msg)
        _log_line('```')
        _log_line()
        _log_line('```')
        _log_line(formatted)
        _log_line('```')
    raise SystemExit(1)


@contextlib.contextmanager
def error_handler():
    try:
        yield
    except (Exception, KeyboardInterrupt) as e:
        if isinstance(e, FatalError):
            msg = 'An error has occurred'
        elif isinstance(e, KeyboardInterrupt):
            msg = 'Interrupted (^C)'
        else:
            msg = 'An unexpected error has occurred'
        _log_and_exit(msg, e, traceback.format_exc())
