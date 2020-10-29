import multiprocessing
import os.path
import sys
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import CalledProcessError
from testing.auto_namedtuple import auto_namedtuple


@pytest.fixture
def find_exe_mck():
    with mock.patch.object(parse_shebang, 'find_executable') as mck:
        yield mck


@pytest.fixture
def homedir_mck():
    def fake_expanduser(pth):
        assert pth == '~'
        return os.path.normpath('/home/me')

    with mock.patch.object(os.path, 'expanduser', fake_expanduser):
        yield


def test_exe_exists_does_not_exist(find_exe_mck, homedir_mck):
    find_exe_mck.return_value = None
    assert helpers.exe_exists('ruby') is False


def test_exe_exists_exists(find_exe_mck, homedir_mck):
    find_exe_mck.return_value = os.path.normpath('/usr/bin/ruby')
    assert helpers.exe_exists('ruby') is True


def test_exe_exists_false_if_shim(find_exe_mck, homedir_mck):
    find_exe_mck.return_value = os.path.normpath('/foo/shims/ruby')
    assert helpers.exe_exists('ruby') is False


def test_exe_exists_false_if_homedir(find_exe_mck, homedir_mck):
    find_exe_mck.return_value = os.path.normpath('/home/me/somedir/ruby')
    assert helpers.exe_exists('ruby') is False


def test_exe_exists_commonpath_raises_ValueError(find_exe_mck, homedir_mck):
    find_exe_mck.return_value = os.path.normpath('/usr/bin/ruby')
    with mock.patch.object(os.path, 'commonpath', side_effect=ValueError):
        assert helpers.exe_exists('ruby') is True


def test_exe_exists_true_when_homedir_is_slash(find_exe_mck):
    find_exe_mck.return_value = os.path.normpath('/usr/bin/ruby')
    with mock.patch.object(os.path, 'expanduser', return_value=os.sep):
        assert helpers.exe_exists('ruby') is True


def test_basic_get_default_version():
    assert helpers.basic_get_default_version() == C.DEFAULT


def test_basic_healthy():
    assert helpers.basic_healthy(Prefix('.'), 'default') is True


def test_failed_setup_command_does_not_unicode_error():
    script = (
        'import sys\n'
        "getattr(sys.stderr, 'buffer', sys.stderr).write(b'\\x81\\xfe')\n"
        'exit(1)\n'
    )

    # an assertion that this does not raise `UnicodeError`
    with pytest.raises(CalledProcessError):
        helpers.run_setup_cmd(Prefix('.'), (sys.executable, '-c', script))


def test_assert_no_additional_deps():
    with pytest.raises(AssertionError) as excinfo:
        helpers.assert_no_additional_deps('lang', ['hmmm'])
    msg, = excinfo.value.args
    assert msg == (
        'For now, pre-commit does not support additional_dependencies for lang'
    )


SERIAL_FALSE = auto_namedtuple(require_serial=False)
SERIAL_TRUE = auto_namedtuple(require_serial=True)


def test_target_concurrency_normal():
    with mock.patch.object(multiprocessing, 'cpu_count', return_value=123):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert helpers.target_concurrency(SERIAL_FALSE) == 123


def test_target_concurrency_cpu_count_require_serial_true():
    with mock.patch.dict(os.environ, {}, clear=True):
        assert helpers.target_concurrency(SERIAL_TRUE) == 1


def test_target_concurrency_testing_env_var():
    with mock.patch.dict(
            os.environ, {'PRE_COMMIT_NO_CONCURRENCY': '1'}, clear=True,
    ):
        assert helpers.target_concurrency(SERIAL_FALSE) == 1


def test_target_concurrency_on_travis():
    with mock.patch.dict(os.environ, {'TRAVIS': '1'}, clear=True):
        assert helpers.target_concurrency(SERIAL_FALSE) == 2


def test_target_concurrency_cpu_count_not_implemented():
    with mock.patch.object(
            multiprocessing, 'cpu_count', side_effect=NotImplementedError,
    ):
        with mock.patch.dict(os.environ, {}, clear=True):
            assert helpers.target_concurrency(SERIAL_FALSE) == 1


def test_shuffled_is_deterministic():
    seq = [str(i) for i in range(10)]
    expected = ['4', '0', '5', '1', '8', '6', '2', '3', '7', '9']
    assert helpers._shuffled(seq) == expected
