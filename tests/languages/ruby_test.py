import os.path

from pre_commit.languages import ruby
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from testing.util import xfailif_windows_no_ruby


@xfailif_windows_no_ruby
def test_install_rbenv(tempdir_factory):
    prefix = Prefix(tempdir_factory.get())
    ruby._install_rbenv(prefix)
    # Should have created rbenv directory
    assert os.path.exists(prefix.path('rbenv-default'))

    # Should be able to activate using our script and access rbenv
    with ruby.in_env(prefix, 'default'):
        cmd_output('rbenv', '--help')


@xfailif_windows_no_ruby
def test_install_rbenv_with_version(tempdir_factory):
    prefix = Prefix(tempdir_factory.get())
    ruby._install_rbenv(prefix, version='1.9.3p547')

    # Should be able to activate and use rbenv install
    with ruby.in_env(prefix, '1.9.3p547'):
        cmd_output('rbenv', 'install', '--help')
