from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import os.path
import traceback

import six

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
        _to_bytes(exc), b'\n',
    ))
    output.write(error_msg)
    store = Store()
    store.require_created()
    log_path = os.path.join(store.directory, 'pre-commit.log')
    output.write_line('Check the log at {}'.format(log_path))
    with open(log_path, 'wb') as log:
        output.write(error_msg, stream=log)
        output.write_line(formatted, stream=log)
    raise SystemExit(1)


@contextlib.contextmanager
def error_handler():
    try:
        yield
    except FatalError as e:
        _log_and_exit('An error has occurred', e, traceback.format_exc())
    except Exception as e:
        _log_and_exit(
            'An unexpected error has occurred', e, traceback.format_exc(),
        )
