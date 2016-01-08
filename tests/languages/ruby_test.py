# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os.path

from pre_commit.languages.ruby import _install_rbenv
from testing.util import xfailif_windows_no_ruby


@xfailif_windows_no_ruby
def test_install_rbenv(cmd_runner):
    _install_rbenv(cmd_runner)
    # Should have created rbenv directory
    assert os.path.exists(cmd_runner.path('rbenv-default'))
    # We should have created our `activate` script
    activate_path = cmd_runner.path('rbenv-default', 'bin', 'activate')
    assert os.path.exists(activate_path)

    # Should be able to activate using our script and access rbenv
    cmd_runner.run(
        [
            'bash',
            '-c',
            ". '{prefix}rbenv-default/bin/activate' && rbenv --help",
        ],
    )


@xfailif_windows_no_ruby
def test_install_rbenv_with_version(cmd_runner):
    _install_rbenv(cmd_runner, version='1.9.3p547')

    # Should be able to activate and use rbenv install
    cmd_runner.run(
        [
            'bash',
            '-c',
            ". '{prefix}rbenv-1.9.3p547/bin/activate' && rbenv install --help",
        ],
    )
