
import contextlib
from plumbum import local
from plumbum.machines.session import ShellSession
from pre_commit.languages import helpers

PY_ENV = 'py_env'


@contextlib.contextmanager
def in_env():
    with ShellSession(local['bash'].popen()) as env:
        env.run('source {0}/bin/activate'.format(PY_ENV))
        yield env


def install_environment():
    assert local.path('setup.py').exists()
    # Return immediately if we already have a virtualenv
    if local.path('py_env').exists():
        return

    # Install a virtualenv
    local['virtualenv'][PY_ENV]()

    with in_env() as env:
        # Run their setup.py
        env.run('pip install .')


def run_hook(hook, file_args):
    with in_env() as env:
        # TODO: batch filenames
        return helpers.run_hook(env, hook, file_args)