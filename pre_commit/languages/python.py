
from plumbum import local
import subprocess

PY_ENV = 'py_env'


def install_environment():
    assert local.path('setup.py').exists()
    # Return immediately if we already have a virtualenv
    if local.path(PY_ENV).exists():
        return

    # Install a virtualenv
    local['virtualenv'][PY_ENV]()
    local['bash']['-c', 'source {0}/bin/activate && pip install .'.format(PY_ENV)]()


def run_hook(hook, file_args):
    # TODO: batch filenames
    process = subprocess.Popen(
        ['bash', '-c', ' '.join(
            ['source {0}/bin/activate &&'.format(PY_ENV)] +
            [hook['entry']] + hook.get('args', []) + list(file_args)
        )],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    ret = process.communicate()

    return (process.returncode,) + ret

    return local['bash'][
        '-c', ' '.join(
            ['source {0}/bin/activate &&'.format(PY_ENV)] +
            [hook['entry']] + hook.get('args', []) + list(file_args)
        )
    ].run()