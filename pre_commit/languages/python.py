
from plumbum import local

PY_ENV = 'py_env'


def install_environment():
    assert local.path('setup.py').exists()
    # Return immediately if we already have a virtualenv
    if local.path('py_env').exists():
        return

    # Install a virtualenv
    local['virtualenv'][PY_ENV]()
    local['bash']['-c', 'source {0}/bin/activate && pip install .'.format(PY_ENV)]()


def run_hook(hook, file_args):
    # TODO: batch filenames
    return local['bash'][
        '-c', ' '.join(
            ['source {0}/bin/activate &&'.format(PY_ENV)] +
            [hook['entry']] + hook.get('args', []) + list(file_args)
        )
    ].run()