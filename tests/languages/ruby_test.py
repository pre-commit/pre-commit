import os.path

from pre_commit.languages.ruby import _install_rbenv
from testing.util import skipif_slowtests_false


@skipif_slowtests_false
def test_install_rbenv(cmd_runner):
    _install_rbenv(cmd_runner)
    # Should have created rbenv directory
    assert os.path.exists(cmd_runner.path('rbenv'))
    # It should be a git checkout
    assert os.path.exists(cmd_runner.path('rbenv', '.git'))
    # We should have created our `activate` script
    activate_path = cmd_runner.path('rbenv', 'bin', 'activate')
    assert os.path.exists(activate_path)

    # Should be able to activate using our script and access the install method
    cmd_runner.run(
        [
            'bash',
            '-c',
            '. {prefix}/rbenv/bin/activate && rbenv install --help',
        ],
    )
