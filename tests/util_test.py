import mock
import pytest
import os
import os.path
import random
import sys
from plumbum import local

from pre_commit.util import clean_path_on_failure
from pre_commit.util import entry
from pre_commit.util import memoize_by_cwd


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
    with local.cwd('.git'):
        ret2 = memoized_by_cwd('baz')

    assert ret != ret2


@pytest.fixture
def entry_func():
    @entry
    def func(argv):
        return argv

    return func


def test_explicitly_passed_argv_are_passed(entry_func):
    input = object()
    ret = entry_func(input)
    assert ret is input


def test_no_arguments_passed_uses_argv(entry_func):
    argv = [1, 2, 3, 4]
    with mock.patch.object(sys, 'argv', argv):
        ret = entry_func()
        assert ret == argv[1:]


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
