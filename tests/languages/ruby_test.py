import os.path
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.languages import ruby
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from testing.util import xfailif_windows


ACTUAL_GET_DEFAULT_VERSION = ruby.get_default_version.__wrapped__


@pytest.fixture
def find_exe_mck():
    with mock.patch.object(parse_shebang, 'find_executable') as mck:
        yield mck


def test_uses_default_version_when_not_available(find_exe_mck):
    find_exe_mck.return_value = None
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


def test_uses_system_if_both_gem_and_ruby_are_available(find_exe_mck):
    find_exe_mck.return_value = '/path/to/exe'
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


@xfailif_windows  # pragma: win32 no cover
def test_install_rbenv(tempdir_factory):
    prefix = Prefix(tempdir_factory.get())
    ruby._install_rbenv(prefix, C.DEFAULT)
    # Should have created rbenv directory
    assert os.path.exists(prefix.path('rbenv-default'))

    # Should be able to activate using our script and access rbenv
    with ruby.in_env(prefix, 'default'):
        cmd_output('rbenv', '--help')


@xfailif_windows  # pragma: win32 no cover
def test_install_rbenv_with_version(tempdir_factory):
    prefix = Prefix(tempdir_factory.get())
    ruby._install_rbenv(prefix, version='1.9.3p547')

    # Should be able to activate and use rbenv install
    with ruby.in_env(prefix, '1.9.3p547'):
        cmd_output('rbenv', 'install', '--help')
