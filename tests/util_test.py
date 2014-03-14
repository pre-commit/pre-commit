
import pytest
import random
from plumbum import local

from pre_commit.util import cached_property
from pre_commit.util import memoize_by_cwd


@pytest.fixture
def class_with_cached_property():
    class Foo(object):
        @cached_property
        def foo(self):
            return "Foo" + str(random.getrandbits(64))

    return Foo


def test_cached_property(class_with_cached_property):
    instance = class_with_cached_property()
    val = instance.foo
    val2 = instance.foo
    assert val is val2


def test_unbound_cached_property(class_with_cached_property):
    # Make sure we don't blow up when accessing the property unbound
    prop = class_with_cached_property.foo
    assert isinstance(prop, cached_property)


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
