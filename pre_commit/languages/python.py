
import contexlib
from plumbum import local

PY_ENV = 'py_env'


class PythonEnv(object):
    def __init__(self):
        self.env_prefix = '. {0}/bin/activate &&'.format(PY_ENV)

    def run(self, cmd):
        return local['bash']['-c', ' '.join([self.env_prefix, cmd])]()


NODE_ENV = 'node_env'

class NodeEnv(object):
    def __init__(self, py_env):
        self.py_env = py_env
        self.env_prefix = '. {0}/bin/activate &&'.format(NODE_ENV)

    def run(self, cmd):
        return self.py_env.run(' '.join(self.env_prefix, cmd))


@contexlib.contextmanager
def in_env():
    yield PythonEnv()


def install_environment():
    assert local.path('setup.py').exists()
    # Return immediately if we already have a virtualenv
    if local.path(PY_ENV).exists():
        return

    # Install a virtualenv
    local['virtualenv'][PY_ENV]()
    with in_env() as env:
        env.run('pip install .')


def run_hook(hook, file_args):
    # TODO: batch filenames
    with in_env() as env:
        env = env
        # MAGIC
        pass
