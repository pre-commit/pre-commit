from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os.path
import mock
import pytest
import re

from pre_commit import error_handler
from pre_commit.errors import FatalError


@pytest.yield_fixture
def mocked_log_and_exit():
    with mock.patch.object(error_handler, '_log_and_exit') as log_and_exit:
        yield log_and_exit


def test_error_handler_no_exception(mocked_log_and_exit):
    with error_handler.error_handler():
        pass
    assert mocked_log_and_exit.call_count == 0


def test_error_handler_fatal_error(mocked_log_and_exit):
    exc = FatalError('just a test')
    with error_handler.error_handler():
        raise exc

    mocked_log_and_exit.assert_called_once_with(
        'An error has occurred',
        exc,
        # Tested below
        mock.ANY,
    )

    assert re.match(
        'Traceback \(most recent call last\):\n'
        '  File ".+/pre_commit/error_handler.py", line \d+, in error_handler\n'
        '    yield\n'
        '  File ".+/tests/error_handler_test.py", line \d+, '
        'in test_error_handler_fatal_error\n'
        '    raise exc\n'
        '(pre_commit\.errors\.)?FatalError: just a test\n',
        mocked_log_and_exit.call_args[0][2],
    )


def test_error_handler_uncaught_error(mocked_log_and_exit):
    exc = ValueError('another test')
    with error_handler.error_handler():
        raise exc

    mocked_log_and_exit.assert_called_once_with(
        'An unexpected error has occurred',
        exc,
        # Tested below
        mock.ANY,
    )
    assert re.match(
        'Traceback \(most recent call last\):\n'
        '  File ".+/pre_commit/error_handler.py", line \d+, in error_handler\n'
        '    yield\n'
        '  File ".+/tests/error_handler_test.py", line \d+, '
        'in test_error_handler_uncaught_error\n'
        '    raise exc\n'
        'ValueError: another test\n',
        mocked_log_and_exit.call_args[0][2],
    )


def test_log_and_exit(mock_out_store_directory):
    mocked_print = mock.Mock()
    with pytest.raises(error_handler.PreCommitSystemExit):
        error_handler._log_and_exit(
            'msg', FatalError('hai'), "I'm a stacktrace",
            print_fn=mocked_print,
        )

    printed = '\n'.join(call[0][0] for call in mocked_print.call_args_list)
    assert printed == (
        'msg: FatalError: hai\n'
        'Check the log at ~/.pre-commit/pre-commit.log'
    )

    log_file = os.path.join(mock_out_store_directory, 'pre-commit.log')
    assert os.path.exists(log_file)
    contents = io.open(log_file).read()
    assert contents == (
        'msg: FatalError: hai\n'
        "I'm a stacktrace\n"
    )
