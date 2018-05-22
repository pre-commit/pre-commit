from __future__ import absolute_import
from __future__ import unicode_literals

import sys

import pytest

from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import CalledProcessError


def test_basic_get_default_version():
    assert helpers.basic_get_default_version() == 'default'


def test_basic_healthy():
    assert helpers.basic_healthy(None, None) is True


def test_failed_setup_command_does_not_unicode_error():
    script = (
        'import sys\n'
        "getattr(sys.stderr, 'buffer', sys.stderr).write(b'\\x81\\xfe')\n"
        'exit(1)\n'
    )

    # an assertion that this does not raise `UnicodeError`
    with pytest.raises(CalledProcessError):
        helpers.run_setup_cmd(Prefix('.'), (sys.executable, '-c', script))
