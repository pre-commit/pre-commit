from __future__ import unicode_literals

import pytest
import os
import os.path
import random

from pre_commit.util import clean_path_on_failure
from pre_commit.util import cwd
from pre_commit.util import memoize_by_cwd
from pre_commit.util import shell_escape
from pre_commit.util import tmpdir


@pytest.fixture
def memoized_by_cwd():
    @memoize_by_cwd
    def func(arg):
        return arg + str(random.getrandbits(64))

    return func


def test_memoized_by_cwd_returns_same_twice_in_a_row(memoized_by_cwd):
    ret = memoized_by_cwd('baz')
    ret2 = memoized_by_cwd('baz')
    assert ret is ret2


def test_memoized_by_cwd_returns_different_for_different_args(memoized_by_cwd):
    ret = memoized_by_cwd('baz')
    ret2 = memoized_by_cwd('bar')
    assert ret.startswith('baz')
    assert ret2.startswith('bar')
    assert ret != ret2


def test_memoized_by_cwd_changes_with_different_cwd(memoized_by_cwd):
    ret = memoized_by_cwd('baz')
    with cwd('.git'):
        ret2 = memoized_by_cwd('baz')

    assert ret != ret2


def test_clean_on_failure_noop(in_tmpdir):
    with clean_path_on_failure('foo'):
        pass


def test_clean_path_on_failure_does_nothing_when_not_raising(in_tmpdir):
    with clean_path_on_failure('foo'):
        os.mkdir('foo')
    assert os.path.exists('foo')


def test_clean_path_on_failure_cleans_for_normal_exception(in_tmpdir):
    class MyException(Exception):
        pass

    with pytest.raises(MyException):
        with clean_path_on_failure('foo'):
            os.mkdir('foo')
            raise MyException

    assert not os.path.exists('foo')


def test_clean_path_on_failure_cleans_for_system_exit(in_tmpdir):
    class MySystemExit(SystemExit):
        pass

    with pytest.raises(MySystemExit):
        with clean_path_on_failure('foo'):
            os.mkdir('foo')
            raise MySystemExit

    assert not os.path.exists('foo')


@pytest.mark.parametrize(
    ('input_str', 'expected'),
    (
        ('', "''"),
        ('foo"bar', "'foo\"bar'"),
        ("foo'bar", "'foo'\"'\"'bar'")
    ),
)
def test_shell_escape(input_str, expected):
    assert shell_escape(input_str) == expected


def test_tmpdir():
    with tmpdir() as tempdir:
        assert os.path.exists(tempdir)
    assert not os.path.exists(tempdir)
