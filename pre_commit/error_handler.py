from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import io
import os.path
import traceback

from pre_commit import five
from pre_commit.errors import FatalError
from pre_commit.output import sys_stdout_write_wrapper
from pre_commit.store import Store


# For testing purposes
class PreCommitSystemExit(SystemExit):
    pass


def _to_bytes(exc):
    try:
        return bytes(exc)
    except Exception:
        return five.text(exc).encode('UTF-8')


def _log_and_exit(msg, exc, formatted, write_fn=sys_stdout_write_wrapper):
    error_msg = b''.join((
        five.to_bytes(msg), b': ',
        five.to_bytes(type(exc).__name__), b': ',
        _to_bytes(exc), b'\n',
    ))
    write_fn(error_msg)
    write_fn('Check the log at ~/.pre-commit/pre-commit.log\n')
    store = Store()
    store.require_created()
    with io.open(os.path.join(store.directory, 'pre-commit.log'), 'wb') as log:
        log.write(five.to_bytes(error_msg))
        log.write(five.to_bytes(formatted) + b'\n')
    raise PreCommitSystemExit(1)


@contextlib.contextmanager
def error_handler():
    try:
        yield
    except FatalError as e:
        _log_and_exit('An error has occurred', e, traceback.format_exc())
    except Exception as e:
        _log_and_exit(
            'An unexpected error has occurred',
            e,
            traceback.format_exc(),
        )
