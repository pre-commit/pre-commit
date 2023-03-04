from __future__ import annotations

import os.path
import sys
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.languages import python
from pre_commit.prefix import Prefix
from pre_commit.util import make_executable
from pre_commit.util import win_exe
from testing.language_helpers import run_language


def test_read_pyvenv_cfg(tmpdir):
    pyvenv_cfg = tmpdir.join('pyvenv.cfg')
    pyvenv_cfg.write(
        '# I am a comment\n'
        '\n'
        'foo = bar\n'
        'version-info=123\n',
    )
    expected = {'foo': 'bar', 'version-info': '123'}
    assert python._read_pyvenv_cfg(pyvenv_cfg) == expected


def test_read_pyvenv_cfg_non_utf8(tmpdir):
    pyvenv_cfg = tmpdir.join('pyvenv_cfg')
    pyvenv_cfg.write_binary('hello = hello john.š\n'.encode())
    expected = {'hello': 'hello john.š'}
    assert python._read_pyvenv_cfg(pyvenv_cfg) == expected


def test_norm_version_expanduser():
    home = os.path.expanduser('~')
    if sys.platform == 'win32':  # pragma: win32 cover
        path = r'~\python343'
        expected_path = fr'{home}\python343'
    else:  # pragma: win32 no cover
        path = '~/.pyenv/versions/3.4.3/bin/python'
        expected_path = f'{home}/.pyenv/versions/3.4.3/bin/python'
    result = python.norm_version(path)
    assert result == expected_path


def test_norm_version_of_default_is_sys_executable():
    assert python.norm_version('default') is None


@pytest.mark.parametrize('v', ('python3.9', 'python3', 'python'))
def test_sys_executable_matches(v):
    with mock.patch.object(sys, 'version_info', (3, 9, 10)):
        assert python._sys_executable_matches(v)
        assert python.norm_version(v) is None


@pytest.mark.parametrize('v', ('notpython', 'python3.x'))
def test_sys_executable_matches_does_not_match(v):
    with mock.patch.object(sys, 'version_info', (3, 9, 10)):
        assert not python._sys_executable_matches(v)


@pytest.mark.parametrize(
    ('exe', 'realpath', 'expected'), (
        ('/usr/bin/python3', '/usr/bin/python3.7', 'python3'),
        ('/usr/bin/python', '/usr/bin/python3.7', 'python3.7'),
        ('/usr/bin/python', '/usr/bin/python', None),
        ('/usr/bin/python3.7m', '/usr/bin/python3.7m', 'python3.7m'),
        ('v/bin/python', 'v/bin/pypy', 'pypy'),
    ),
)
def test_find_by_sys_executable(exe, realpath, expected):
    with mock.patch.object(sys, 'executable', exe):
        with mock.patch.object(os.path, 'realpath', return_value=realpath):
            with mock.patch.object(python, 'find_executable', lambda x: x):
                assert python._find_by_sys_executable() == expected


@pytest.fixture
def python_dir(tmpdir):
    with tmpdir.as_cwd():
        prefix = tmpdir.join('prefix').ensure_dir()
        prefix.join('setup.py').write('import setuptools; setuptools.setup()')
        prefix = Prefix(str(prefix))
        yield prefix, tmpdir


def test_healthy_default_creator(python_dir):
    prefix, tmpdir = python_dir

    python.install_environment(prefix, C.DEFAULT, ())

    # should be healthy right after creation
    assert python.health_check(prefix, C.DEFAULT) is None

    # even if a `types.py` file exists, should still be healthy
    tmpdir.join('types.py').ensure()
    assert python.health_check(prefix, C.DEFAULT) is None


def test_healthy_venv_creator(python_dir):
    # venv creator produces slightly different pyvenv.cfg
    prefix, tmpdir = python_dir

    with envcontext((('VIRTUALENV_CREATOR', 'venv'),)):
        python.install_environment(prefix, C.DEFAULT, ())

    assert python.health_check(prefix, C.DEFAULT) is None


def test_unhealthy_python_goes_missing(python_dir):
    prefix, tmpdir = python_dir

    python.install_environment(prefix, C.DEFAULT, ())

    exe_name = win_exe('python')
    py_exe = prefix.path(python.bin_dir('py_env-default'), exe_name)
    os.remove(py_exe)

    ret = python.health_check(prefix, C.DEFAULT)
    assert ret == (
        f'virtualenv python version did not match created version:\n'
        f'- actual version: <<error retrieving version from {py_exe}>>\n'
        f'- expected version: {python._version_info(sys.executable)}\n'
    )


def test_unhealthy_with_version_change(python_dir):
    prefix, tmpdir = python_dir

    python.install_environment(prefix, C.DEFAULT, ())

    with open(prefix.path('py_env-default/pyvenv.cfg'), 'a+') as f:
        f.write('version_info = 1.2.3\n')

    ret = python.health_check(prefix, C.DEFAULT)
    assert ret == (
        f'virtualenv python version did not match created version:\n'
        f'- actual version: {python._version_info(sys.executable)}\n'
        f'- expected version: 1.2.3\n'
    )


def test_unhealthy_system_version_changes(python_dir):
    prefix, tmpdir = python_dir

    python.install_environment(prefix, C.DEFAULT, ())

    with open(prefix.path('py_env-default/pyvenv.cfg'), 'a') as f:
        f.write('base-executable = /does/not/exist\n')

    ret = python.health_check(prefix, C.DEFAULT)
    assert ret == (
        f'base executable python version does not match created version:\n'
        f'- base-executable version: <<error retrieving version from /does/not/exist>>\n'  # noqa: E501
        f'- expected version: {python._version_info(sys.executable)}\n'
    )


def test_unhealthy_old_virtualenv(python_dir):
    prefix, tmpdir = python_dir

    python.install_environment(prefix, C.DEFAULT, ())

    # simulate "old" virtualenv by deleting this file
    os.remove(prefix.path('py_env-default/pyvenv.cfg'))

    ret = python.health_check(prefix, C.DEFAULT)
    assert ret == 'pyvenv.cfg does not exist (old virtualenv?)'


def test_unhealthy_unexpected_pyvenv(python_dir):
    prefix, tmpdir = python_dir

    python.install_environment(prefix, C.DEFAULT, ())

    # simulate a buggy environment build (I don't think this is possible)
    with open(prefix.path('py_env-default/pyvenv.cfg'), 'w'):
        pass

    ret = python.health_check(prefix, C.DEFAULT)
    assert ret == "created virtualenv's pyvenv.cfg is missing `version_info`"


def test_unhealthy_then_replaced(python_dir):
    prefix, tmpdir = python_dir

    python.install_environment(prefix, C.DEFAULT, ())

    # simulate an exe which returns an old version
    exe_name = win_exe('python')
    py_exe = prefix.path(python.bin_dir('py_env-default'), exe_name)
    os.rename(py_exe, f'{py_exe}.tmp')

    with open(py_exe, 'w') as f:
        f.write('#!/usr/bin/env bash\necho 1.2.3\n')
    make_executable(py_exe)

    # should be unhealthy due to version mismatch
    ret = python.health_check(prefix, C.DEFAULT)
    assert ret == (
        f'virtualenv python version did not match created version:\n'
        f'- actual version: 1.2.3\n'
        f'- expected version: {python._version_info(sys.executable)}\n'
    )

    # now put the exe back and it should be healthy again
    os.replace(f'{py_exe}.tmp', py_exe)

    assert python.health_check(prefix, C.DEFAULT) is None


def test_language_versioned_python_hook(tmp_path):
    setup_py = '''\
from setuptools import setup
setup(
    name='example',
    py_modules=['mod'],
    entry_points={'console_scripts': ['myexe=mod:main']},
)
'''
    tmp_path.joinpath('setup.py').write_text(setup_py)
    tmp_path.joinpath('mod.py').write_text('def main(): print("ohai")')

    # we patch this to force virtualenv executing with `-p` since we can't
    # reliably have multiple pythons available in CI
    with mock.patch.object(
            python,
            '_sys_executable_matches',
            return_value=False,
    ):
        assert run_language(tmp_path, python, 'myexe') == (0, b'ohai\n')
