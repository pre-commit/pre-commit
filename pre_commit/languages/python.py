from __future__ import unicode_literals

import contextlib
import distutils.spawn
import os
import sys

import virtualenv

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import shell_escape


ENVIRONMENT_DIR = 'py_env'


class PythonEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return ". '{{prefix}}{0}activate' &&".format(
            virtualenv.path_locations(
                helpers.environment_dir(ENVIRONMENT_DIR, self.language_version)
            )[-1].rstrip(os.sep) + os.sep,
        )


@contextlib.contextmanager
def in_env(repo_cmd_runner, language_version):
    yield PythonEnv(repo_cmd_runner, language_version)


def norm_version(version):
    if os.name == 'nt':  # pragma: no cover (windows)
        # Try looking up by name
        if distutils.spawn.find_executable(version):
            return version

        # If it is in the form pythonx.x search in the default
        # place on windows
        if version.startswith('python'):
            return r'C:\{0}\python.exe'.format(version.replace('.', ''))

        # Otherwise assume it is a path
    return os.path.expanduser(version)


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=None,
):
    assert repo_cmd_runner.exists('setup.py')
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    # Install a virtualenv
    with clean_path_on_failure(repo_cmd_runner.path(directory)):
        venv_cmd = [
            sys.executable, '-m', 'virtualenv',
            '{{prefix}}{0}'.format(directory)
        ]
        if version != 'default':
            venv_cmd.extend(['-p', norm_version(version)])
        repo_cmd_runner.run(venv_cmd)
        with in_env(repo_cmd_runner, version) as env:
            env.run("cd '{prefix}' && pip install .")
            if additional_dependencies:
                env.run(
                    "cd '{prefix}' && pip install " +
                    ' '.join(
                        shell_escape(dep) for dep in additional_dependencies
                    )
                )


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner, hook['language_version']) as env:
        return helpers.run_hook(env, hook, file_args)
