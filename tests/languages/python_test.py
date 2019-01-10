from __future__ import absolute_import
from __future__ import unicode_literals

import os.path
import sys

import mock
import pytest

from pre_commit.languages import python


def test_norm_version_expanduser():
    home = os.path.expanduser('~')
    if os.name == 'nt':  # pragma: no cover (nt)
        path = r'~\python343'
        expected_path = r'{}\python343'.format(home)
    else:  # pragma: windows no cover
        path = '~/.pyenv/versions/3.4.3/bin/python'
        expected_path = home + '/.pyenv/versions/3.4.3/bin/python'
    result = python.norm_version(path)
    assert result == expected_path


@pytest.mark.parametrize('v', ('python3.6', 'python3', 'python'))
def test_sys_executable_matches(v):
    with mock.patch.object(sys, 'version_info', (3, 6, 7)):
        assert python._sys_executable_matches(v)


@pytest.mark.parametrize('v', ('notpython', 'python3.x'))
def test_sys_executable_matches_does_not_match(v):
    with mock.patch.object(sys, 'version_info', (3, 6, 7)):
        assert not python._sys_executable_matches(v)
