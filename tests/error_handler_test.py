# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os.path
import re
import sys

import mock
import pytest

from pre_commit import error_handler
from pre_commit import five
from pre_commit.errors import FatalError
from testing.util import cmd_output_mocked_pre_commit_home


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
        r'Traceback \(most recent call last\):\n'
        r'  File ".+pre_commit.error_handler.py", line \d+, in error_handler\n'
        r'    yield\n'
        r'  File ".+tests.error_handler_test.py", line \d+, '
        r'in test_error_handler_fatal_error\n'
        r'    raise exc\n'
        r'(pre_commit\.errors\.)?FatalError: just a test\n',
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
        r'Traceback \(most recent call last\):\n'
        r'  File ".+pre_commit.error_handler.py", line \d+, in error_handler\n'
        r'    yield\n'
        r'  File ".+tests.error_handler_test.py", line \d+, '
        r'in test_error_handler_uncaught_error\n'
        r'    raise exc\n'
        r'ValueError: another test\n',
        mocked_log_and_exit.call_args[0][2],
    )


def test_log_and_exit(mock_out_store_directory):
    mocked_write = mock.Mock()
    with pytest.raises(error_handler.PreCommitSystemExit):
        error_handler._log_and_exit(
            'msg', FatalError('hai'), "I'm a stacktrace",
            write_fn=mocked_write,
        )

    printed = ''.join(
        five.to_text(call[0][0]) for call in mocked_write.call_args_list
    )
    assert printed == (
        'msg: FatalError: hai\n'
        'Check the log at ~/.pre-commit/pre-commit.log\n'
    )

    log_file = os.path.join(mock_out_store_directory, 'pre-commit.log')
    assert os.path.exists(log_file)
    contents = io.open(log_file).read()
    assert contents == (
        'msg: FatalError: hai\n'
        "I'm a stacktrace\n"
    )


def test_error_handler_non_ascii_exception(mock_out_store_directory):
    with pytest.raises(error_handler.PreCommitSystemExit):
        with error_handler.error_handler():
            raise ValueError('☃')


def test_error_handler_no_tty(tempdir_factory):
    output = cmd_output_mocked_pre_commit_home(
        sys.executable, '-c',
        'from __future__ import unicode_literals\n'
        'from pre_commit.error_handler import error_handler\n'
        'with error_handler():\n'
        '    raise ValueError("\\u2603")\n',
        retcode=1,
        tempdir_factory=tempdir_factory,
    )
    assert output[1].replace('\r', '') == (
        'An unexpected error has occurred: ValueError: ☃\n'
        'Check the log at ~/.pre-commit/pre-commit.log\n'
    )
