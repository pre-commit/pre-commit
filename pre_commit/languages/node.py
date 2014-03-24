import contextlib
from plumbum import local

from pre_commit.languages import helpers
from pre_commit.languages import python


NODE_ENV = 'node_env'


class NodeEnv(python.PythonEnv):
    @property
    def env_prefix(self):
        base = super(NodeEnv, self).env_prefix
        return ' '.join([base, '. {0}/bin/activate &&'.format(NODE_ENV)])


@contextlib.contextmanager
def in_env():
    yield NodeEnv()


def install_environment():
    assert local.path('package.json').exists()

    if local.path(NODE_ENV).exists():
        return

    local['virtualenv'][python.PY_ENV]()

    with python.in_env() as python_env:
        python_env.run('pip install nodeenv')

        # Try and use the system level node executable first
        retcode, _, _ = python_env.run('nodeenv -n system {0}'.format(NODE_ENV))
        # TODO: log failure here
        # cleanup
        if retcode:
            local.path(NODE_ENV).delete()
            python_env.run('nodeenv --jobs 4 {0}'.format(NODE_ENV))

        with in_env() as node_env:
            node_env.run('npm install -g')


def run_hook(hook, file_args):
    with in_env() as node_env:
        return helpers.run_hook(node_env, hook, file_args)
