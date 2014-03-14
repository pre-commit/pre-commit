
import pytest
import time

from pre_commit.util import cached_property


@pytest.fixture
def class_with_cached_property():
    class Foo(object):
        @cached_property
        def foo(self):
            return "Foo" + str(time.time())

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

