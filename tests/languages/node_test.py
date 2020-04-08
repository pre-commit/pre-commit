import sys
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.languages.node import get_default_version


ACTUAL_GET_DEFAULT_VERSION = get_default_version.__wrapped__


@pytest.fixture
def is_linux():
    with mock.patch.object(sys, 'platform', 'linux'):
        yield


@pytest.fixture
def is_win32():
    with mock.patch.object(sys, 'platform', 'win32'):
        yield


@pytest.fixture
def find_exe_mck():
    with mock.patch.object(parse_shebang, 'find_executable') as mck:
        yield mck


@pytest.mark.usefixtures('is_linux')
def test_sets_system_when_node_and_npm_are_available(find_exe_mck):
    find_exe_mck.return_value = '/path/to/exe'
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


@pytest.mark.usefixtures('is_linux')
def test_uses_default_when_node_and_npm_are_not_available(find_exe_mck):
    find_exe_mck.return_value = None
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


@pytest.mark.usefixtures('is_win32')
def test_sets_default_on_windows(find_exe_mck):
    find_exe_mck.return_value = '/path/to/exe'
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT
