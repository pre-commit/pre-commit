
import contextlib

from pre_commit.languages import helpers


PY_ENV = 'py_env'


class PythonEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return '. {{prefix}}{0}/bin/activate &&'.format(PY_ENV)


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    yield PythonEnv(repo_cmd_runner)


def install_environment(repo_cmd_runner):
    assert repo_cmd_runner.exists('setup.py')
    # Return immediately if we already have a virtualenv
    if repo_cmd_runner.exists(PY_ENV):
        return

    # Install a virtualenv
    repo_cmd_runner.run(['virtualenv', '{{prefix}}{0}'.format(PY_ENV)])
    with in_env(repo_cmd_runner) as env:
        env.run('cd {prefix} && pip install .')


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner) as env:
        return helpers.run_hook(env, hook, file_args)
