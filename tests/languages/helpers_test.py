from __future__ import absolute_import
from __future__ import unicode_literals

import multiprocessing
import os
import sys

import mock
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


def test_target_concurrency_normal():
    with mock.patch.object(multiprocessing, 'cpu_count', return_value=123):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert helpers.target_concurrency({'require_serial': False}) == 123


def test_target_concurrency_cpu_count_require_serial_true():
    with mock.patch.dict(os.environ, {}, clear=True):
        assert helpers.target_concurrency({'require_serial': True}) == 1


def test_target_concurrency_testing_env_var():
    with mock.patch.dict(
            os.environ, {'PRE_COMMIT_NO_CONCURRENCY': '1'}, clear=True,
    ):
        assert helpers.target_concurrency({'require_serial': False}) == 1


def test_target_concurrency_on_travis():
    with mock.patch.dict(os.environ, {'TRAVIS': '1'}, clear=True):
        assert helpers.target_concurrency({'require_serial': False}) == 2


def test_target_concurrency_cpu_count_not_implemented():
    with mock.patch.object(
            multiprocessing, 'cpu_count', side_effect=NotImplementedError,
    ):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert helpers.target_concurrency({'require_serial': False}) == 1


def test_shuffled_is_deterministic():
    assert helpers._shuffled(range(10)) == [3, 7, 8, 2, 4, 6, 5, 1, 0, 9]
