
import contextlib
from plumbum import local
from pre_commit.languages import helpers

PY_ENV = 'py_env'


class PythonEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return '. {0}/bin/activate &&'.format(PY_ENV)


@contextlib.contextmanager
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
    with in_env() as env:
        return helpers.run_hook(env, hook, file_args)
