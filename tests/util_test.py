from __future__ import annotations

import os.path
import stat
import subprocess

import pytest

from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b
from pre_commit.util import cmd_output_p
from pre_commit.util import make_executable
from pre_commit.util import rmtree


def test_CalledProcessError_str():
    error = CalledProcessError(1, ('exe',), b'output\n', b'errors\n')
    assert str(error) == (
        "command: ('exe',)\n"
        'return code: 1\n'
        'stdout:\n'
        '    output\n'
        'stderr:\n'
        '    errors'
    )


def test_CalledProcessError_str_nooutput():
    error = CalledProcessError(1, ('exe',), b'', b'')
    assert str(error) == (
        "command: ('exe',)\n"
        'return code: 1\n'
        'stdout: (none)\n'
        'stderr: (none)'
    )


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


def test_cmd_output_exe_not_found():
    ret, out, _ = cmd_output('dne', check=False)
    assert ret == 1
    assert out == 'Executable `dne` not found'


@pytest.mark.parametrize('fn', (cmd_output_b, cmd_output_p))
def test_cmd_output_exe_not_found_bytes(fn):
    ret, out, _ = fn('dne', check=False, stderr=subprocess.STDOUT)
    assert ret == 1
    assert out == b'Executable `dne` not found'


@pytest.mark.parametrize('fn', (cmd_output_b, cmd_output_p))
def test_cmd_output_no_shebang(tmpdir, fn):
    f = tmpdir.join('f').ensure()
    make_executable(f)

    # previously this raised `OSError` -- the output is platform specific
    ret, out, _ = fn(str(f), check=False, stderr=subprocess.STDOUT)
    assert ret == 1
    assert isinstance(out, bytes)
    assert out.endswith(b'\n')


def test_rmtree_read_only_directories(tmpdir):
    """Simulates the go module tree.  See #1042"""
    tmpdir.join('x/y/z').ensure_dir().join('a').ensure()
    mode = os.stat(str(tmpdir.join('x'))).st_mode
    mode_no_w = mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
    tmpdir.join('x/y/z').chmod(mode_no_w)
    tmpdir.join('x/y/z').chmod(mode_no_w)
    tmpdir.join('x/y/z').chmod(mode_no_w)
    rmtree(str(tmpdir.join('x')))
