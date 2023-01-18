from __future__ import annotations

import sys

import pytest

from pre_commit.languages import lua
from pre_commit.util import make_executable
from testing.language_helpers import run_language

pytestmark = pytest.mark.skipif(
    sys.platform == 'win32',
    reason='lua is not supported on windows',
)


def test_lua(tmp_path):  # pragma: win32 no cover
    rockspec = '''\
package = "hello"
version = "dev-1"

source = {
   url = "git+ssh://git@github.com/pre-commit/pre-commit.git"
}
description = {}
dependencies = {}
build = {
    type = "builtin",
    modules = {},
    install = {
        bin = {"bin/hello-world-lua"}
    },
}
'''
    hello_world_lua = '''\
#!/usr/bin/env lua
print('hello world')
'''
    tmp_path.joinpath('hello-dev-1.rockspec').write_text(rockspec)
    bin_dir = tmp_path.joinpath('bin')
    bin_dir.mkdir()
    bin_file = bin_dir.joinpath('hello-world-lua')
    bin_file.write_text(hello_world_lua)
    make_executable(bin_file)

    expected = (0, b'hello world\n')
    assert run_language(tmp_path, lua, 'hello-world-lua') == expected


def test_lua_additional_dependencies(tmp_path):  # pragma: win32 no cover
    ret, out = run_language(
        tmp_path,
        lua,
        'luacheck --version',
        deps=('luacheck',),
    )
    assert ret == 0
    assert out.startswith(b'Luacheck: ')
