from __future__ import annotations

import sys
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit import parse_shebang
from pre_commit.languages import bun
from pre_commit.prefix import Prefix
from pre_commit.store import _make_local_repo
from testing.language_helpers import run_language


ACTUAL_GET_DEFAULT_VERSION = bun.get_default_version.__wrapped__


@pytest.fixture
def find_exe_mck():
    with mock.patch.object(parse_shebang, 'find_executable') as mck:
        yield mck


def test_sets_system_when_bun_is_available(find_exe_mck):
    find_exe_mck.return_value = '/path/to/exe'
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


def test_uses_default_when_bun_is_not_available(find_exe_mck):
    find_exe_mck.return_value = None
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


def _make_hello_world(tmp_path):
    """Create a simple Node/Bun package for testing."""
    package_json = '''\
{
    "name": "test-bun-hook",
    "version": "1.0.0",
    "bin": {"bun-hello": "./bin/bun-hello.js"}
}
'''
    bin_script = '''\
#!/usr/bin/env node
console.log('Hello World');
'''

    tmp_path.joinpath('package.json').write_text(package_json)
    bin_dir = tmp_path.joinpath('bin')
    bin_dir.mkdir()
    bin_dir.joinpath('bun-hello.js').write_text(bin_script)


def test_bun_default_version():
    """Test default version detection."""
    version = bun.get_default_version()
    # Should return either 'system' or 'default'
    assert version in {'system', 'default'}


@pytest.mark.skipif(
    not lang_base.exe_exists('bun'),
    reason='bun not installed on system',
)
def test_bun_hook_system(tmp_path):
    """Test running a hook with system Bun."""
    _make_hello_world(tmp_path)
    ret = run_language(tmp_path, bun, 'bun-hello')
    assert ret == (0, b'Hello World\n')


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='Test may be slow on Windows',
)
def test_bun_hook_default_version(tmp_path):
    """Test running a hook with downloaded Bun (default/latest)."""
    _make_hello_world(tmp_path)
    ret = run_language(tmp_path, bun, 'bun-hello', version=C.DEFAULT)
    assert ret == (0, b'Hello World\n')


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason='Test may be slow on Windows',
)
def test_bun_hook_specific_version(tmp_path):
    """Test running a hook with specific Bun version."""
    _make_hello_world(tmp_path)
    # Use a known stable version
    ret = run_language(tmp_path, bun, 'bun-hello', version='1.1.42')
    assert ret == (0, b'Hello World\n')


def test_bun_additional_dependencies(tmp_path):
    """Test installing additional dependencies."""
    _make_local_repo(str(tmp_path))
    ret, out = run_language(
        tmp_path,
        bun,
        'bun pm ls -g',
        deps=('lodash',),
    )
    assert b'lodash' in out


def test_bun_with_package_json_only(tmp_path):
    """Test that package.json is required."""
    # Don't create package.json - just create a Prefix
    prefix = Prefix(str(tmp_path))

    with pytest.raises(AssertionError):
        bun.install_environment(prefix, 'system', ())


def test_environment_dir():
    """Test ENVIRONMENT_DIR is set correctly."""
    assert bun.ENVIRONMENT_DIR == 'bunenv'


def test_run_hook_uses_basic():
    """Test that run_hook is set to basic implementation."""
    assert bun.run_hook is lang_base.basic_run_hook


@pytest.mark.skipif(
    not lang_base.exe_exists('bun'),
    reason='bun not installed on system',
)
def test_bun_health_check_success(tmp_path):
    """Test health check with valid environment."""
    _make_hello_world(tmp_path)

    _make_local_repo(str(tmp_path))
    prefix = Prefix(str(tmp_path))
    bun.install_environment(prefix, 'system', ())

    health = bun.health_check(prefix, 'system')
    assert health is None  # None means healthy
