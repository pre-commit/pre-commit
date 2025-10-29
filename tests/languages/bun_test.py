from __future__ import annotations

import os
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


def test_get_platform_darwin():
    """Test platform detection for macOS."""
    with mock.patch.object(sys, 'platform', 'darwin'):
        assert bun._get_platform() == 'darwin'


def test_get_platform_linux():
    """Test platform detection for Linux."""
    with mock.patch.object(sys, 'platform', 'linux'):
        assert bun._get_platform() == 'linux'


def test_get_platform_linux_with_suffix():
    """Test platform detection for Linux with version suffix."""
    with mock.patch.object(sys, 'platform', 'linux2'):
        assert bun._get_platform() == 'linux'


def test_get_platform_windows():
    """Test platform detection for Windows."""
    with mock.patch.object(sys, 'platform', 'win32'):
        assert bun._get_platform() == 'windows'


def test_get_platform_unsupported():
    """Test platform detection fails for unsupported platform."""
    with mock.patch.object(sys, 'platform', 'freebsd'):
        with pytest.raises(
            AssertionError, match='Unsupported platform: freebsd',
        ):
            bun._get_platform()


def test_normalize_version_default():
    """Test version normalization for default version."""
    assert bun._normalize_version(C.DEFAULT) == 'latest'


def test_normalize_version_latest():
    """Test version normalization for 'latest' string.

    Note: 'latest' as a direct string gets treated as a version tag,
    not as the special latest keyword. Use C.DEFAULT for that.
    """
    assert bun._normalize_version('latest') == 'bun-vlatest'


def test_normalize_version_plain_number():
    """Test version normalization for plain version number."""
    assert bun._normalize_version('1.1.42') == 'bun-v1.1.42'


def test_normalize_version_with_v_prefix():
    """Test version normalization for version with 'v' prefix."""
    assert bun._normalize_version('v1.1.42') == 'bun-v1.1.42'


def test_normalize_version_with_bun_v_prefix():
    """Test version normalization for version already with 'bun-v' prefix."""
    assert bun._normalize_version('bun-v1.1.42') == 'bun-v1.1.42'


def test_install_bun_invalid_version_raises_error(tmp_path):
    """Test that installing invalid Bun version raises ValueError."""
    import urllib.error

    # Create a mock HTTPError with 404 status
    mock_error = urllib.error.HTTPError(
        url='https://github.com/oven-sh/bun/releases/'
            'download/bun-v99.99.99/bun-darwin-x64.zip',
        code=404,
        msg='Not Found',
        hdrs=None,  # type: ignore
        fp=None,
    )

    with mock.patch('urllib.request.urlopen', side_effect=mock_error):
        with pytest.raises(
            ValueError, match='Could not find Bun version',
        ):
            bun._install_bun('99.99.99', str(tmp_path))


def test_install_bun_other_http_error_propagates(tmp_path):
    """Test that non-404 HTTP errors are propagated."""
    import urllib.error

    # Create a mock HTTPError with 500 status
    mock_error = urllib.error.HTTPError(
        url='https://github.com/oven-sh/bun/releases/'
            'download/bun-v1.1.42/bun-darwin-x64.zip',
        code=500,
        msg='Internal Server Error',
        hdrs=None,  # type: ignore
        fp=None,
    )

    with mock.patch('urllib.request.urlopen', side_effect=mock_error):
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            bun._install_bun('1.1.42', str(tmp_path))
        assert exc_info.value.code == 500


def test_install_bun_no_bun_directory_found(tmp_path):
    """Test extraction works even if no bun directory found."""
    from unittest.mock import MagicMock

    dest = str(tmp_path / 'bunenv')
    os.makedirs(dest, exist_ok=True)

    # Create a file after extraction (not a bun- directory)
    (tmp_path / 'bunenv' / 'some-other-file.txt').write_text('content')

    # Create a mock zip file that does nothing on extractall
    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.extractall = MagicMock()

    with mock.patch('urllib.request.urlopen') as mock_urlopen, \
            mock.patch('shutil.copyfileobj'), \
            mock.patch('zipfile.ZipFile', return_value=mock_zipfile):

        # Mock urlopen to return a fake response
        mock_response = MagicMock()
        mock_urlopen.return_value = mock_response

        # Should complete without error (loop exits)
        bun._install_bun('1.1.42', dest)

        # Verify bin directory was still created
        assert os.path.exists(os.path.join(dest, 'bin'))


def test_install_bun_missing_executable_in_directory(tmp_path):
    """Test extraction handles missing executable gracefully."""
    from unittest.mock import MagicMock

    dest = str(tmp_path / 'bunenv')
    os.makedirs(dest, exist_ok=True)

    # Create a bun directory without the executable
    bun_dir = tmp_path / 'bunenv' / 'bun-darwin-x64'
    bun_dir.mkdir()
    (bun_dir / 'README.md').write_text('readme')

    # Create a mock zip file that does nothing
    mock_zipfile = MagicMock()
    mock_zipfile.__enter__.return_value = mock_zipfile
    mock_zipfile.__exit__.return_value = None
    mock_zipfile.extractall = MagicMock()

    with mock.patch('urllib.request.urlopen') as mock_urlopen, \
            mock.patch('shutil.copyfileobj'), \
            mock.patch('zipfile.ZipFile', return_value=mock_zipfile):

        mock_response = MagicMock()
        mock_urlopen.return_value = mock_response

        # Should complete without error
        bun._install_bun('1.1.42', dest)

        # Verify the bun directory was still removed
        assert not bun_dir.exists()


@pytest.mark.skipif(
    not lang_base.exe_exists('bun'),
    reason='bun not installed on system',
)
def test_install_environment_system_version_skips_download(tmp_path):
    """Test that system version doesn't download Bun binary."""
    _make_hello_world(tmp_path)
    _make_local_repo(str(tmp_path))
    prefix = Prefix(str(tmp_path))

    # Mock _install_bun to ensure it's never called
    with mock.patch.object(bun, '_install_bun') as mock_install:
        bun.install_environment(prefix, 'system', ())

        # Verify _install_bun was NOT called
        mock_install.assert_not_called()

    # Verify environment still works
    assert bun.health_check(prefix, 'system') is None


def test_install_environment_system_version_skips_download_mock(tmp_path):
    """Test that system version doesn't download Bun binary (mocked)."""
    _make_hello_world(tmp_path)
    _make_local_repo(str(tmp_path))
    prefix = Prefix(str(tmp_path))

    # Mock all the bun commands to avoid needing system bun
    with mock.patch.object(bun, '_install_bun') as mock_install, \
            mock.patch('pre_commit.lang_base.setup_cmd'):

        bun.install_environment(prefix, 'system', ())

        # Verify _install_bun was NOT called for system version
        mock_install.assert_not_called()
