import os.path
import tarfile
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.languages import ruby
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from pre_commit.util import resource_bytesio
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


@pytest.fixture
def fake_gem_prefix(tmpdir):
    gemspec = '''\
Gem::Specification.new do |s|
    s.name = 'pre_commit_placeholder_package'
    s.version = '0.0.0'
    s.summary = 'placeholder gem for pre-commit hooks'
    s.authors = ['Anthony Sottile']
end
'''
    tmpdir.join('placeholder_gem.gemspec').write(gemspec)
    yield Prefix(tmpdir)


@xfailif_windows  # pragma: win32 no cover
def test_install_ruby_system(fake_gem_prefix):
    ruby.install_environment(fake_gem_prefix, 'system', ())

    # Should be able to activate and use rbenv install
    with ruby.in_env(fake_gem_prefix, 'system'):
        _, out, _ = cmd_output('gem', 'list')
        assert 'pre_commit_placeholder_package' in out


@xfailif_windows  # pragma: win32 no cover
def test_install_ruby_default(fake_gem_prefix):
    ruby.install_environment(fake_gem_prefix, C.DEFAULT, ())
    # Should have created rbenv directory
    assert os.path.exists(fake_gem_prefix.path('rbenv-default'))

    # Should be able to activate using our script and access rbenv
    with ruby.in_env(fake_gem_prefix, 'default'):
        cmd_output('rbenv', '--help')


@xfailif_windows  # pragma: win32 no cover
def test_install_ruby_with_version(fake_gem_prefix):
    ruby.install_environment(fake_gem_prefix, '2.7.2', ())

    # Should be able to activate and use rbenv install
    with ruby.in_env(fake_gem_prefix, '2.7.2'):
        cmd_output('rbenv', 'install', '--help')


@pytest.mark.parametrize(
    'filename',
    ('rbenv.tar.gz', 'ruby-build.tar.gz', 'ruby-download.tar.gz'),
)
def test_archive_root_stat(filename):
    with resource_bytesio(filename) as f:
        with tarfile.open(fileobj=f) as tarf:
            root, _, _ = filename.partition('.')
            assert oct(tarf.getmember(root).mode) == '0o755'
