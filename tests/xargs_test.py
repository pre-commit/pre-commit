from __future__ import absolute_import
from __future__ import unicode_literals

import pytest

from pre_commit import xargs


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


def test_xargs_retcode_normal():
    ret, _, _ = xargs.xargs(exit_cmd, ('0',), _max_length=max_length)
    assert ret == 0

    ret, _, _ = xargs.xargs(exit_cmd, ('0', '1'), _max_length=max_length)
    assert ret == 1
