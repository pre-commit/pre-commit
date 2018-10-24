# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import sys

import mock
import pytest
import six

from pre_commit import xargs


@pytest.fixture
def win32_py2_mock():
    with mock.patch.object(sys, 'getfilesystemencoding', return_value='utf-8'):
        with mock.patch.object(sys, 'platform', 'win32'):
            with mock.patch.object(six, 'PY2', True):
                yield


@pytest.fixture
def win32_py3_mock():
    with mock.patch.object(sys, 'getfilesystemencoding', return_value='utf-8'):
        with mock.patch.object(sys, 'platform', 'win32'):
            with mock.patch.object(six, 'PY2', False):
                yield


@pytest.fixture
def linux_mock():
    with mock.patch.object(sys, 'getfilesystemencoding', return_value='utf-8'):
        with mock.patch.object(sys, 'platform', 'linux'):
            yield


def test_partition_trivial():
    assert xargs.partition(('cmd',), ()) == (('cmd',),)


def test_partition_simple():
    assert xargs.partition(('cmd',), ('foo',)) == (('cmd', 'foo'),)


def test_partition_limits():
    ret = xargs.partition(
        ('ninechars',), (
            # Just match the end (with spaces)
            '.' * 5, '.' * 4,
            # Just match the end (single arg)
            '.' * 10,
            # Goes over the end
            '.' * 5,
            '.' * 6,
        ),
        _max_length=20,
    )
    assert ret == (
        ('ninechars', '.' * 5, '.' * 4),
        ('ninechars', '.' * 10),
        ('ninechars', '.' * 5),
        ('ninechars', '.' * 6),
    )


def test_partition_limit_win32_py3(win32_py3_mock):
    cmd = ('ninechars',)
    # counted as half because of utf-16 encode
    varargs = ('😑' * 5,)
    ret = xargs.partition(cmd, varargs, _max_length=20)
    assert ret == (cmd + varargs,)


def test_partition_limit_win32_py2(win32_py2_mock):
    cmd = ('ninechars',)
    varargs = ('😑' * 5,)  # 4 bytes * 5
    ret = xargs.partition(cmd, varargs, _max_length=30)
    assert ret == (cmd + varargs,)


def test_partition_limit_linux(linux_mock):
    cmd = ('ninechars',)
    varargs = ('😑' * 5,)
    ret = xargs.partition(cmd, varargs, _max_length=30)
    assert ret == (cmd + varargs,)


def test_argument_too_long_with_large_unicode(linux_mock):
    cmd = ('ninechars',)
    varargs = ('😑' * 10,)  # 4 bytes * 10
    with pytest.raises(xargs.ArgumentTooLongError):
        xargs.partition(cmd, varargs, _max_length=20)


def test_argument_too_long():
    with pytest.raises(xargs.ArgumentTooLongError):
        xargs.partition(('a' * 5,), ('a' * 5,), _max_length=10)


def test_xargs_smoke():
    ret, out, err = xargs.xargs(('echo',), ('hello', 'world'))
    assert ret == 0
    assert out == b'hello world\n'
    assert err == b''


exit_cmd = ('bash', '-c', 'exit $1', '--')
# Abuse max_length to control the exit code
max_length = len(' '.join(exit_cmd)) + 2


def test_xargs_negate():
    ret, _, _ = xargs.xargs(
        exit_cmd, ('1',), negate=True, _max_length=max_length,
    )
    assert ret == 0

    ret, _, _ = xargs.xargs(
        exit_cmd, ('1', '0'), negate=True, _max_length=max_length,
    )
    assert ret == 1


def test_xargs_negate_command_not_found():
    ret, _, _ = xargs.xargs(('cmd-not-found',), ('1',), negate=True)
    assert ret != 0


def test_xargs_retcode_normal():
    ret, _, _ = xargs.xargs(exit_cmd, ('0',), _max_length=max_length)
    assert ret == 0

    ret, _, _ = xargs.xargs(exit_cmd, ('0', '1'), _max_length=max_length)
    assert ret == 1
