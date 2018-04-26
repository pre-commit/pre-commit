from __future__ import absolute_import
from __future__ import unicode_literals

import os.path

import pytest

from pre_commit.languages import python


def test_norm_version_expanduser():
    home = os.path.expanduser('~')
    if os.name == 'nt':  # pragma: no cover (nt)
        path = r'~\python343'
        expected_path = r'{}\python343'.format(home)
    else:  # pragma: no cover (non-nt)
        path = '~/.pyenv/versions/3.4.3/bin/python'
        expected_path = home + '/.pyenv/versions/3.4.3/bin/python'
    result = python.norm_version(path)
    assert result == (expected_path, False)


@pytest.mark.parametrize(
    'version,use_venv', [
        ('python3.6', False),
        ('python3.6+venv', True),
    ],
)
def test_norm_version_venv(version, use_venv):
    assert python.norm_version(version)[1] == use_venv
