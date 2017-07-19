from __future__ import absolute_import
from __future__ import unicode_literals

from pre_commit.languages import helpers


def test_basic_get_default_version():
    assert helpers.basic_get_default_version() == 'default'


def test_basic_healthy():
    assert helpers.basic_healthy(None, None) is True
