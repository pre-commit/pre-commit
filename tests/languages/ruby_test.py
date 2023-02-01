from __future__ import annotations

import tarfile
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.envcontext import envcontext
from pre_commit.languages import ruby
from pre_commit.store import _make_local_repo
from pre_commit.util import resource_bytesio
from testing.language_helpers import run_language
from testing.util import cwd
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


@pytest.mark.parametrize(
    'filename',
    ('rbenv.tar.gz', 'ruby-build.tar.gz', 'ruby-download.tar.gz'),
)
def test_archive_root_stat(filename):
    with resource_bytesio(filename) as f:
        with tarfile.open(fileobj=f) as tarf:
            root, _, _ = filename.partition('.')
            assert oct(tarf.getmember(root).mode) == '0o755'


def _setup_hello_world(tmp_path):
    bin_dir = tmp_path.joinpath('bin')
    bin_dir.mkdir()
    bin_dir.joinpath('ruby_hook').write_text(
        '#!/usr/bin/env ruby\n'
        "puts 'Hello world from a ruby hook'\n",
    )
    gemspec = '''\
Gem::Specification.new do |s|
    s.name = 'ruby_hook'
    s.version = '0.1.0'
    s.authors = ['Anthony Sottile']
    s.summary = 'A ruby hook!'
    s.description = 'A ruby hook!'
    s.files = ['bin/ruby_hook']
    s.executables = ['ruby_hook']
end
'''
    tmp_path.joinpath('ruby_hook.gemspec').write_text(gemspec)


def test_ruby_hook_system(tmp_path):
    assert ruby.get_default_version() == 'system'

    _setup_hello_world(tmp_path)

    ret = run_language(tmp_path, ruby, 'ruby_hook')
    assert ret == (0, b'Hello world from a ruby hook\n')


def test_ruby_with_user_install_set(tmp_path):
    gemrc = tmp_path.joinpath('gemrc')
    gemrc.write_text('gem: --user-install\n')

    with envcontext((('GEMRC', str(gemrc)),)):
        test_ruby_hook_system(tmp_path)


def test_ruby_additional_deps(tmp_path):
    _make_local_repo(tmp_path)

    ret = run_language(
        tmp_path,
        ruby,
        'ruby -e',
        args=('require "tins"',),
        deps=('tins',),
    )
    assert ret == (0, b'')


@xfailif_windows  # pragma: win32 no cover
def test_ruby_hook_default(tmp_path):
    _setup_hello_world(tmp_path)

    out, ret = run_language(tmp_path, ruby, 'rbenv --help', version='default')
    assert out == 0
    assert ret.startswith(b'Usage: rbenv ')


@xfailif_windows  # pragma: win32 no cover
def test_ruby_hook_language_version(tmp_path):
    _setup_hello_world(tmp_path)
    tmp_path.joinpath('bin', 'ruby_hook').write_text(
        '#!/usr/bin/env ruby\n'
        'puts RUBY_VERSION\n'
        "puts 'Hello world from a ruby hook'\n",
    )

    ret = run_language(tmp_path, ruby, 'ruby_hook', version='3.2.0')
    assert ret == (0, b'3.2.0\nHello world from a ruby hook\n')


@xfailif_windows  # pragma: win32 no cover
def test_ruby_with_bundle_disable_shared_gems(tmp_path):
    workdir = tmp_path.joinpath('workdir')
    workdir.mkdir()
    # this needs a `source` or there's a deprecation warning
    # silencing this with `BUNDLE_GEMFILE` breaks some tools (#2739)
    workdir.joinpath('Gemfile').write_text('source ""\ngem "lol_hai"\n')
    # this bundle config causes things to be written elsewhere
    bundle = workdir.joinpath('.bundle')
    bundle.mkdir()
    bundle.joinpath('config').write_text(
        'BUNDLE_DISABLE_SHARED_GEMS: true\n'
        'BUNDLE_PATH: vendor/gem\n',
    )

    with cwd(workdir):
        # `3.2.0` has new enough `gem` reading `.bundle`
        test_ruby_hook_language_version(tmp_path)
