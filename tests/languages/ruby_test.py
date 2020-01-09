import os.path
import pipes

from pre_commit.languages.ruby import _install_rbenv
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output
from testing.util import xfailif_windows_no_ruby


@xfailif_windows_no_ruby
def test_install_rbenv(tempdir_factory):
    prefix = Prefix(tempdir_factory.get())
    _install_rbenv(prefix)
    # Should have created rbenv directory
    assert os.path.exists(prefix.path('rbenv-default'))
    # We should have created our `activate` script
    activate_path = prefix.path('rbenv-default', 'bin', 'activate')
    assert os.path.exists(activate_path)

    # Should be able to activate using our script and access rbenv
    cmd_output(
        'bash', '-c',
        '. {} && rbenv --help'.format(
            pipes.quote(prefix.path('rbenv-default', 'bin', 'activate')),
        ),
    )


@xfailif_windows_no_ruby
def test_install_rbenv_with_version(tempdir_factory):
    prefix = Prefix(tempdir_factory.get())
    _install_rbenv(prefix, version='1.9.3p547')

    # Should be able to activate and use rbenv install
    cmd_output(
        'bash', '-c',
        '. {} && rbenv install --help'.format(
            pipes.quote(prefix.path('rbenv-1.9.3p547', 'bin', 'activate')),
        ),
    )
