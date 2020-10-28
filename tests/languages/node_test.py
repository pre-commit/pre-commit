import json
import os
import shutil
import sys
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import envcontext
from pre_commit import parse_shebang
from pre_commit.languages import node
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from testing.util import xfailif_windows


ACTUAL_GET_DEFAULT_VERSION = node.get_default_version.__wrapped__


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


@xfailif_windows  # pragma: win32 no cover
def test_healthy_system_node(tmpdir):
    tmpdir.join('package.json').write('{"name": "t", "version": "1.0.0"}')

    prefix = Prefix(str(tmpdir))
    node.install_environment(prefix, 'system', ())
    assert node.healthy(prefix, 'system')


@xfailif_windows  # pragma: win32 no cover
def test_unhealthy_if_system_node_goes_missing(tmpdir):
    bin_dir = tmpdir.join('bin').ensure_dir()
    node_bin = bin_dir.join('node')
    node_bin.mksymlinkto(shutil.which('node'))

    prefix_dir = tmpdir.join('prefix').ensure_dir()
    prefix_dir.join('package.json').write('{"name": "t", "version": "1.0.0"}')

    path = ('PATH', (str(bin_dir), os.pathsep, envcontext.Var('PATH')))
    with envcontext.envcontext((path,)):
        prefix = Prefix(str(prefix_dir))
        node.install_environment(prefix, 'system', ())
        assert node.healthy(prefix, 'system')

        node_bin.remove()
        assert not node.healthy(prefix, 'system')


@xfailif_windows  # pragma: win32 no cover
def test_installs_without_links_outside_env(tmpdir):
    tmpdir.join('bin/main.js').ensure().write(
        '#!/usr/bin/env node\n'
        '_ = require("lodash"); console.log("success!")\n',
    )
    tmpdir.join('package.json').write(
        json.dumps({
            'name': 'foo',
            'version': '0.0.1',
            'bin': {'foo': './bin/main.js'},
            'dependencies': {'lodash': '*'},
        }),
    )

    prefix = Prefix(str(tmpdir))
    node.install_environment(prefix, 'system', ())
    assert node.healthy(prefix, 'system')

    # this directory shouldn't exist, make sure we succeed without it existing
    cmd_output('rm', '-rf', str(tmpdir.join('node_modules')))

    with node.in_env(prefix, 'system'):
        assert cmd_output('foo')[1] == 'success!\n'
