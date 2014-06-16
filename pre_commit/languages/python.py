from __future__ import unicode_literals

import contextlib

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure


ENVIRONMENT_DIR = 'py_env'


class PythonEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return '. {{prefix}}{0}/bin/activate &&'.format(ENVIRONMENT_DIR)


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    yield PythonEnv(repo_cmd_runner)


def install_environment(repo_cmd_runner, version='default'):
    assert repo_cmd_runner.exists('setup.py')

    # Install a virtualenv
    with clean_path_on_failure(repo_cmd_runner.path(ENVIRONMENT_DIR)):
        venv_cmd = ['virtualenv', '{{prefix}}{0}'.format(ENVIRONMENT_DIR)]
        if version != 'default':
            venv_cmd.extend(['-p', version])
        repo_cmd_runner.run(venv_cmd)
        with in_env(repo_cmd_runner) as env:
            env.run('cd {prefix} && pip install .')


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner) as env:
        return helpers.run_hook(env, hook, file_args)
