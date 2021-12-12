import os
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit.languages import lua
from testing.util import xfailif_windows


@pytest.mark.parametrize(
    'lua_name', ('lua', 'lua5.4', 'lua-5.4', 'lua5.4.exe'),
)
def test_find_lua(tmp_path, lua_name):
    """The language support can find common lua executable names."""
    lua_file = tmp_path / lua_name
    lua_file.touch(0o555)
    with mock.patch.dict(os.environ, {'PATH': str(tmp_path)}):
        lua_executable = lua._find_lua(C.DEFAULT)
    assert lua_name in lua_executable


def test_find_lua_language_version(tmp_path):
    """Language discovery can find a specific version."""
    lua_file = tmp_path / 'lua5.99'
    lua_file.touch(0o555)
    with mock.patch.dict(os.environ, {'PATH': str(tmp_path)}):
        lua_executable = lua._find_lua('5.99')
    assert 'lua5.99' in lua_executable


@pytest.mark.parametrize(
    ('invalid', 'mode'),
    (
        ('foobar', 0o555),
        ('luac', 0o555),
        # Windows doesn't respect the executable checking.
        pytest.param('lua5.4', 0o444, marks=xfailif_windows),
    ),
)
def test_find_lua_fail(tmp_path, invalid, mode):
    """No lua executable on the system will fail."""
    non_lua_file = tmp_path / invalid
    non_lua_file.touch(mode)
    with mock.patch.dict(os.environ, {'PATH': str(tmp_path)}):
        with pytest.raises(ValueError):
            lua._find_lua(C.DEFAULT)


@mock.patch.object(lua, 'cmd_output')
def test_bad_package_path(mock_cmd_output):
    """A package path missing path info returns an unknown version."""
    mock_cmd_output.return_value = (0, '', '')
    with pytest.raises(ValueError):
        lua._get_lua_path_version('lua')
