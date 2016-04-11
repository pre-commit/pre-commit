from __future__ import unicode_literals

import contextlib
import os
import sys

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'node_env'


def get_env_patch(venv):
    return (
        ('NODE_VIRTUAL_ENV', venv),
        ('NPM_CONFIG_PREFIX', venv),
        ('npm_config_prefix', venv),
        ('NODE_PATH', os.path.join(venv, 'lib', 'node_modules')),
        ('PATH', (os.path.join(venv, 'bin'), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(repo_cmd_runner, language_version):
    envdir = os.path.join(
        repo_cmd_runner.prefix_dir,
        helpers.environment_dir(ENVIRONMENT_DIR, language_version),
    )
    with envcontext(get_env_patch(envdir)):
        yield


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    additional_dependencies = tuple(additional_dependencies)
    assert repo_cmd_runner.exists('package.json')
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    env_dir = repo_cmd_runner.path(directory)
    with clean_path_on_failure(env_dir):
        cmd = [
            sys.executable, '-m', 'nodeenv', '--prebuilt',
            '{{prefix}}{0}'.format(directory),
        ]

        if version != 'default':
            cmd.extend(['-n', version])

        repo_cmd_runner.run(cmd)

        with in_env(repo_cmd_runner, version):
            helpers.run_setup_cmd(
                repo_cmd_runner,
                ('npm', 'install', '-g', '.') + additional_dependencies,
            )


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner, hook['language_version']):
        return xargs((hook['entry'],) + tuple(hook['args']), file_args)
