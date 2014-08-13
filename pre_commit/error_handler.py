from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import io
import os.path
import traceback

from pre_commit.errors import FatalError
from pre_commit.store import Store


# For testing purposes
class PreCommitSystemExit(SystemExit):
    pass


def _log_and_exit(msg, exc, formatted, print_fn=print):
    error_msg = '{0}: {1}: {2}'.format(msg, type(exc).__name__, exc)
    print_fn(error_msg)
    print_fn('Check the log at ~/.pre-commit/pre-commit.log')
    store = Store()
    store.require_created()
    with io.open(os.path.join(store.directory, 'pre-commit.log'), 'w') as log:
        log.write(error_msg + '\n')
        log.write(formatted + '\n')
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
