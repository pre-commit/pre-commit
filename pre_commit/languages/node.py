import contextlib
from plumbum import local

from pre_commit.languages import helpers
from pre_commit.languages import python


NODE_ENV = 'node_env'


class NodeEnv(object):
    def __init__(self, py_env):
        self.py_env = py_env
        self.env_prefix = '. {0}/bin/activate &&'.format(NODE_ENV)

    def run(self, cmd, **kwargs):
        return self.py_env.run(' '.join([self.env_prefix, cmd]), **kwargs)


@contextlib.contextmanager
def in_env(py_env):
    yield NodeEnv(py_env)


def install_environment():
    assert local.path('package.json').exists()

    if local.path('node_env').exists():
        return

    local['virtualenv'][python.PY_ENV]()

    with python.in_env() as python_env:
        python_env.run('pip install nodeenv')
        python_env.run('nodeenv {0}'.format(NODE_ENV))

        with in_env(python_env) as node_env:
            node_env.run('npm install -g')


def run_hook(hook, file_args):
    with python.in_env() as py_env:
        with in_env(py_env) as node_env:
            return helpers.run_hook(node_env, hook, file_args)