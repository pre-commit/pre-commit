import os.path
import re
import sys
from unittest import mock

import pytest

from pre_commit import error_handler
from testing.util import cmd_output_mocked_pre_commit_home


@pytest.fixture
def mocked_log_and_exit():
    with mock.patch.object(error_handler, '_log_and_exit') as log_and_exit:
        yield log_and_exit


def test_error_handler_no_exception(mocked_log_and_exit):
    with error_handler.error_handler():
        pass
    assert mocked_log_and_exit.call_count == 0


def test_error_handler_fatal_error(mocked_log_and_exit):
    exc = error_handler.FatalError('just a test')
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
        r'(pre_commit\.error_handler\.)?FatalError: just a test\n',
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


def test_error_handler_keyboardinterrupt(mocked_log_and_exit):
    exc = KeyboardInterrupt()
    with error_handler.error_handler():
        raise exc

    mocked_log_and_exit.assert_called_once_with(
        'Interrupted (^C)',
        exc,
        # Tested below
        mock.ANY,
    )
    assert re.match(
        r'Traceback \(most recent call last\):\n'
        r'  File ".+pre_commit.error_handler.py", line \d+, in error_handler\n'
        r'    yield\n'
        r'  File ".+tests.error_handler_test.py", line \d+, '
        r'in test_error_handler_keyboardinterrupt\n'
        r'    raise exc\n'
        r'KeyboardInterrupt\n',
        mocked_log_and_exit.call_args[0][2],
    )


def test_log_and_exit(cap_out, mock_store_dir):
    with pytest.raises(SystemExit):
        error_handler._log_and_exit(
            'msg', error_handler.FatalError('hai'), "I'm a stacktrace",
        )

    printed = cap_out.get()
    log_file = os.path.join(mock_store_dir, 'pre-commit.log')
    assert printed == (
        'msg: FatalError: hai\n' 'Check the log at {}\n'.format(log_file)
    )

    assert os.path.exists(log_file)
    with open(log_file) as f:
        logged = f.read()
        expected = (
            r'^### version information\n'
            r'\n'
            r'```\n'
            r'pre-commit version: \d+\.\d+\.\d+\n'
            r'sys.version:\n'
            r'(    .*\n)*'
            r'sys.executable: .*\n'
            r'os.name: .*\n'
            r'sys.platform: .*\n'
            r'```\n'
            r'\n'
            r'### error information\n'
            r'\n'
            r'```\n'
            r'msg: FatalError: hai\n'
            r'```\n'
            r'\n'
            r'```\n'
            r"I'm a stacktrace\n"
            r'```\n'
        )
        assert re.match(expected, logged)


def test_error_handler_non_ascii_exception(mock_store_dir):
    with pytest.raises(SystemExit):
        with error_handler.error_handler():
            raise ValueError('☃')


def test_error_handler_no_tty(tempdir_factory):
    pre_commit_home = tempdir_factory.get()
    ret, out, _ = cmd_output_mocked_pre_commit_home(
        sys.executable,
        '-c',
        'from __future__ import unicode_literals\n'
        'from pre_commit.error_handler import error_handler\n'
        'with error_handler():\n'
        '    raise ValueError("\\u2603")\n',
        retcode=1,
        tempdir_factory=tempdir_factory,
        pre_commit_home=pre_commit_home,
    )
    log_file = os.path.join(pre_commit_home, 'pre-commit.log')
    out_lines = out.splitlines()
    assert out_lines[-2] == 'An unexpected error has occurred: ValueError: ☃'
    assert out_lines[-1] == f'Check the log at {log_file}'
