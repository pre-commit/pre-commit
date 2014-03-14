import contextlib
from plumbum import local
from plumbum.machines.session import ShellSession
from pre_commit.languages import helpers

from pre_commit.languages import python

NODE_ENV = 'node_env'

@contextlib.contextmanager
def in_env():
    with ShellSession(local['bash'].popen()) as env:
        env.run('. {0}/bin/activate'.format(NODE_ENV))
        yield env


def install_environment():
    assert local.path('package.json').exists()

    if local.path('node_env').exists():
        return

    # Install a virtualenv
    local['virtualenv'][python.PY_ENV]()

    with python.in_env() as python_env:
        python_env.run('pip install nodeenv')

        print "Creating nodeenv"
        local['nodeenv'][NODE_ENV]()
        print "Done nodeenv"

        with in_env() as node_env:
            node_env.run('npm install -g')


def run_hook(hook, file_args):
    with python.in_env():
        with in_env() as node_env:
            return helpers.run_hook(node_env, hook, file_args)