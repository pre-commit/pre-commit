import os.path
import stat
import sys
from unittest import mock

import pytest
import re_assert

from pre_commit import error_handler
from pre_commit.errors import FatalError
from pre_commit.store import Store
from pre_commit.util import CalledProcessError
from testing.util import cmd_output_mocked_pre_commit_home
from testing.util import xfailif_windows


@pytest.fixture
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
        1,
        exc,
        # Tested below
        mock.ANY,
    )

    pattern = re_assert.Matches(
        r'Traceback \(most recent call last\):\n'
        r'  File ".+pre_commit.error_handler.py", line \d+, in error_handler\n'
        r'    yield\n'
        r'  File ".+tests.error_handler_test.py", line \d+, '
        r'in test_error_handler_fatal_error\n'
        r'    raise exc\n'
        r'(pre_commit\.errors\.)?FatalError: just a test\n',
    )
    pattern.assert_matches(mocked_log_and_exit.call_args[0][3])


def test_error_handler_uncaught_error(mocked_log_and_exit):
    exc = ValueError('another test')
    with error_handler.error_handler():
        raise exc

    mocked_log_and_exit.assert_called_once_with(
        'An unexpected error has occurred',
        3,
        exc,
        # Tested below
        mock.ANY,
    )
    pattern = re_assert.Matches(
        r'Traceback \(most recent call last\):\n'
        r'  File ".+pre_commit.error_handler.py", line \d+, in error_handler\n'
        r'    yield\n'
        r'  File ".+tests.error_handler_test.py", line \d+, '
        r'in test_error_handler_uncaught_error\n'
        r'    raise exc\n'
        r'ValueError: another test\n',
    )
    pattern.assert_matches(mocked_log_and_exit.call_args[0][3])


def test_error_handler_keyboardinterrupt(mocked_log_and_exit):
    exc = KeyboardInterrupt()
    with error_handler.error_handler():
        raise exc

    mocked_log_and_exit.assert_called_once_with(
        'Interrupted (^C)',
        130,
        exc,
        # Tested below
        mock.ANY,
    )
    pattern = re_assert.Matches(
        r'Traceback \(most recent call last\):\n'
        r'  File ".+pre_commit.error_handler.py", line \d+, in error_handler\n'
        r'    yield\n'
        r'  File ".+tests.error_handler_test.py", line \d+, '
        r'in test_error_handler_keyboardinterrupt\n'
        r'    raise exc\n'
        r'KeyboardInterrupt\n',
    )
    pattern.assert_matches(mocked_log_and_exit.call_args[0][3])


def test_log_and_exit(cap_out, mock_store_dir):
    tb = (
        'Traceback (most recent call last):\n'
        '  File "<stdin>", line 2, in <module>\n'
        'pre_commit.errors.FatalError: hai\n'
    )

    with pytest.raises(SystemExit) as excinfo:
        error_handler._log_and_exit('msg', 1, FatalError('hai'), tb)
    assert excinfo.value.code == 1

    printed = cap_out.get()
    log_file = os.path.join(mock_store_dir, 'pre-commit.log')
    assert printed == f'msg: FatalError: hai\nCheck the log at {log_file}\n'

    assert os.path.exists(log_file)
    with open(log_file) as f:
        logged = f.read()
        pattern = re_assert.Matches(
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
            r'Traceback \(most recent call last\):\n'
            r'  File "<stdin>", line 2, in <module>\n'
            r'pre_commit\.errors\.FatalError: hai\n'
            r'```\n',
        )
        pattern.assert_matches(logged)


def test_error_handler_non_ascii_exception(mock_store_dir):
    with pytest.raises(SystemExit):
        with error_handler.error_handler():
            raise ValueError('☃')


def test_error_handler_non_utf8_exception(mock_store_dir):
    with pytest.raises(SystemExit):
        with error_handler.error_handler():
            raise CalledProcessError(1, ('exe',), 0, b'error: \xa0\xe1', b'')


def test_error_handler_non_stringable_exception(mock_store_dir):
    class C(Exception):
        def __str__(self):
            raise RuntimeError('not today!')

    with pytest.raises(SystemExit):
        with error_handler.error_handler():
            raise C()


def test_error_handler_no_tty(tempdir_factory):
    pre_commit_home = tempdir_factory.get()
    ret, out, _ = cmd_output_mocked_pre_commit_home(
        sys.executable,
        '-c',
        'from pre_commit.error_handler import error_handler\n'
        'with error_handler():\n'
        '    raise ValueError("\\u2603")\n',
        retcode=3,
        tempdir_factory=tempdir_factory,
        pre_commit_home=pre_commit_home,
    )
    log_file = os.path.join(pre_commit_home, 'pre-commit.log')
    out_lines = out.splitlines()
    assert out_lines[-2] == 'An unexpected error has occurred: ValueError: ☃'
    assert out_lines[-1] == f'Check the log at {log_file}'


@xfailif_windows  # pragma: win32 no cover
def test_error_handler_read_only_filesystem(mock_store_dir, cap_out, capsys):
    # a better scenario would be if even the Store crash would be handled
    # but realistically we're only targetting systems where the Store has
    # already been set up
    Store()

    write = (stat.S_IWGRP | stat.S_IWOTH | stat.S_IWUSR)
    os.chmod(mock_store_dir, os.stat(mock_store_dir).st_mode & ~write)

    with pytest.raises(SystemExit):
        with error_handler.error_handler():
            raise ValueError('ohai')

    output = cap_out.get()
    assert output.startswith(
        'An unexpected error has occurred: ValueError: ohai\n'
        'Failed to write to log at ',
    )

    # our cap_out mock is imperfect so the rest of the output goes to capsys
    out, _ = capsys.readouterr()
    # the things that normally go to the log file will end up here
    assert '### version information' in out
