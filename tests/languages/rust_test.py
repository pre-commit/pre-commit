from __future__ import annotations

from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.languages import rust
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output

ACTUAL_GET_DEFAULT_VERSION = rust.get_default_version.__wrapped__


@pytest.fixture
def cmd_output_b_mck():
    with mock.patch.object(rust, 'cmd_output_b') as mck:
        yield mck


def test_sets_system_when_rust_is_available(cmd_output_b_mck):
    cmd_output_b_mck.return_value = (0, b'', b'')
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


def test_uses_default_when_rust_is_not_available(cmd_output_b_mck):
    cmd_output_b_mck.return_value = (127, b'', b'error: not found')
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


@pytest.mark.parametrize('language_version', (C.DEFAULT, '1.56.0'))
def test_installs_with_bootstrapped_rustup(tmpdir, language_version):
    tmpdir.join('src', 'main.rs').ensure().write(
        'fn main() {\n'
        '    println!("Hello, world!");\n'
        '}\n',
    )
    tmpdir.join('Cargo.toml').ensure().write(
        '[package]\n'
        'name = "hello_world"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n',
    )
    prefix = Prefix(str(tmpdir))

    find_executable_exes = []

    original_find_executable = parse_shebang.find_executable

    def mocked_find_executable(exe: str) -> str | None:
        """
        Return `None` the first time `find_executable` is called to ensure
        that the bootstrapping code is executed, then just let the function
        work as normal.

        Also log the arguments to ensure that everything works as expected.
        """
        find_executable_exes.append(exe)
        if len(find_executable_exes) == 1:
            return None
        return original_find_executable(exe)

    with mock.patch.object(parse_shebang, 'find_executable') as find_exe_mck:
        find_exe_mck.side_effect = mocked_find_executable
        rust.install_environment(prefix, language_version, ())
        assert find_executable_exes == ['rustup', 'rustup', 'cargo']

    with rust.in_env(prefix, language_version):
        assert cmd_output('hello_world')[1] == 'Hello, world!\n'


def test_installs_with_existing_rustup(tmpdir):
    tmpdir.join('src', 'main.rs').ensure().write(
        'fn main() {\n'
        '    println!("Hello, world!");\n'
        '}\n',
    )
    tmpdir.join('Cargo.toml').ensure().write(
        '[package]\n'
        'name = "hello_world"\n'
        'version = "0.1.0"\n'
        'edition = "2021"\n',
    )
    prefix = Prefix(str(tmpdir))

    assert parse_shebang.find_executable('rustup') is not None
    rust.install_environment(prefix, '1.56.0', ())
    with rust.in_env(prefix, '1.56.0'):
        assert cmd_output('hello_world')[1] == 'Hello, world!\n'
