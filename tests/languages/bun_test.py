from __future__ import annotations

import json
import os
import shutil
import sys
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import envcontext
from pre_commit import parse_shebang
from pre_commit.languages import bun
from pre_commit.prefix import Prefix
from pre_commit.store import _make_local_repo
from pre_commit.util import cmd_output
from testing.language_helpers import run_language
from testing.util import xfailif_windows


ACTUAL_GET_DEFAULT_VERSION = bun.get_default_version.__wrapped__


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
def test_sets_system_when_bun_and_npm_are_available(find_exe_mck):
    find_exe_mck.return_value = '/path/to/exe'
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


@pytest.mark.usefixtures('is_linux')
def test_uses_default_when_bun_and_npm_are_not_available(find_exe_mck):
    find_exe_mck.return_value = None
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


@pytest.mark.usefixtures('is_win32')
def test_sets_default_on_windows(find_exe_mck):
    find_exe_mck.return_value = '/path/to/exe'
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


@xfailif_windows  # pragma: win32 no cover
def test_healthy_system_bun(tmpdir):
    tmpdir.join('package.json').write('{"name": "t", "version": "1.0.0"}')

    prefix = Prefix(str(tmpdir))
    bun.install_environment(prefix, 'system', ())
    assert bun.health_check(prefix, 'system') is None


@xfailif_windows  # pragma: win32 no cover
def test_unhealthy_if_system_bun_goes_missing(tmpdir):
    bin_dir = tmpdir.join('bin').ensure_dir()
    bun_bin = bin_dir.join('bun')
    bun_bin.mksymlinkto(shutil.which('bun'))

    prefix_dir = tmpdir.join('prefix').ensure_dir()
    prefix_dir.join('package.json').write('{"name": "t", "version": "1.0.0"}')

    path = ('PATH', (str(bin_dir), os.pathsep, envcontext.Var('PATH')))
    with envcontext.envcontext((path,)):
        prefix = Prefix(str(prefix_dir))
        bun.install_environment(prefix, 'system', ())
        assert bun.health_check(prefix, 'system') is None

        bun_bin.remove()
        ret = bun.health_check(prefix, 'system')
        assert ret == '`bun --version` returned 127'


@xfailif_windows  # pragma: win32 no cover
def test_installs_without_links_outside_env(tmpdir):
    tmpdir.join('bin/main.js').ensure().write(
        '#!/usr/bin/env bun\n'
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
    bun.install_environment(prefix, 'system', ())
    assert bun.health_check(prefix, 'system') is None

    # this directory shouldn't exist, make sure we succeed without it existing
    cmd_output('rm', '-rf', str(tmpdir.join('node_modules')))

    with bun.in_env(prefix, 'system'):
        assert cmd_output('foo')[1] == 'success!\n'


def _make_hello_world(tmp_path):
    package_json = '''\
{"name": "t", "version": "0.0.1", "bin": {"bun-hello": "./bin/main.js"}}
'''
    tmp_path.joinpath('package.json').write_text(package_json)
    bin_dir = tmp_path.joinpath('bin')
    bin_dir.mkdir()
    bin_dir.joinpath('main.js').write_text(
        '#!/usr/bin/env bun\n'
        'console.log("Hello World");\n',
    )


def test_bun_hook_system(tmp_path):
    _make_hello_world(tmp_path)
    ret = run_language(tmp_path, bun, 'bun-hello')
    assert ret == (0, b'Hello World\n')


def test_bun_with_user_config_set(tmp_path):
    cfg = tmp_path.joinpath('cfg')
    cfg.write_text('cache=/dne\n')
    with envcontext.envcontext((('NPM_CONFIG_USERCONFIG', str(cfg)),)):
        test_bun_hook_system(tmp_path)


@pytest.mark.parametrize('version', (C.DEFAULT, '18.14.0'))
def test_bun_hook_versions(tmp_path, version):
    _make_hello_world(tmp_path)
    ret = run_language(tmp_path, bun, 'bun-hello', version=version)
    assert ret == (0, b'Hello World\n')


def test_bun_additional_deps(tmp_path):
    _make_local_repo(str(tmp_path))
    ret, out = run_language(tmp_path, bun, 'bun pm ls', deps=('lodash',))
    assert b' lodash@' in out
