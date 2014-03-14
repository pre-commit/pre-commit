
import contextlib
from plumbum import local
from plumbum.machines.session import ShellSession

PY_ENV = 'py_env'


@contextlib.contextmanager
def in_env():
    with ShellSession(local['bash'].popen()) as env:
        env.run('source {0}/bin/activate'.format(PY_ENV))
        yield env


def install_environment():
    assert local.path('setup.py').exists()
    # Install a virtualenv
    local['virtualenv'][PY_ENV]()

    with in_env() as env:
        # Run their setup.py
        env.run('pip install .')


def run_hook(hook, file_args):
    with in_env() as env:
        # TODO: batch filenames
        return env.run(
            ' '.join([hook['entry']] + hook.get('args', []) + list(file_args)),
            retcode=None,
        )