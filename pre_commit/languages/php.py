from __future__ import unicode_literals

import contextlib
import json
import os

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import resource_filename
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'virtphpenv'
VIRT_PHP_PATH = resource_filename('virtphp.phar')
# It's currently impossible to move this file out of homedir
VIRT_PHP_ENVIRONMENTS = os.path.join(
    os.path.expanduser('~'),
    '.virtphp',
    'environments.json'
)


def get_env_patch(venv, language_version):
    patches = (
        ('VIRTPHP_COMPOSER_GLOBAL', '1'),
        ('COMPOSER_HOME', os.path.join(venv, 'composer')),
        ('PHP_INI_SCAN_DIR', os.path.join(venv, 'etc', 'php')),
        ('PATH', (
            os.path.join(venv, 'bin'), os.pathsep,
            os.path.join(venv, 'vendor/bin'), os.pathsep, Var('PATH')
        ))
    )

    return patches


@contextlib.contextmanager
def in_env(repo_cmd_runner, language_version):
    envdir = os.path.join(
        repo_cmd_runner.prefix_dir,
        helpers.environment_dir(ENVIRONMENT_DIR, language_version),
    )

    with envcontext(get_env_patch(envdir, language_version)):
        yield


@contextlib.contextmanager
def cleanup_environment_on_failure(repo_cmd_runner, directory):
    with clean_path_on_failure(repo_cmd_runner.path(directory)):
        with clean_virtphp_environment_on_failure(directory):
            yield


@contextlib.contextmanager
def clean_virtphp_environment_on_failure(directory):
    """VirtPHP keeps an environments.json file that lists the envs that it
    thinks exists, and it will fail to install them if it thinks that one
    exists, even if it does not.
    This file looks like:
    {
        "virtenv-default": {}
    }
    """
    try:
        yield
    except BaseException:
        if os.path.exists(VIRT_PHP_ENVIRONMENTS):
            with open(VIRT_PHP_ENVIRONMENTS, 'r+') as f:
                environments = json.loads(f.read())
                environments = {
                    environment_key: environment_config
                    for environment_key, environment_config
                    in environments.items() if environment_key != directory
                }
                f.seek(0)
                f.write(json.dumps(environments))
                f.truncate()

        raise


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    additional_dependencies = tuple(additional_dependencies)
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    with cleanup_environment_on_failure(repo_cmd_runner, directory):
        virtphp_env_command = [
            'php', VIRT_PHP_PATH, 'create',
            '--install-path', repo_cmd_runner.prefix_dir[:-1],
            directory
        ]

        if version != 'default':
            # TODO: Not sure what the best choice is here. There's doesn't seem
            # to be a canonical way to keep multiple php versions around.
            # It's Different per OS, package manager, etc. language_version
            # as a php bin directory (as shown here) might be sanest?
            virtphp_env_command.extend(
                ['--php-bin-dir', os.path.realpath(version)]
            )

        repo_cmd_runner.run(virtphp_env_command, cwd='/')
        with in_env(repo_cmd_runner, version):
            helpers.run_setup_cmd(
                repo_cmd_runner,
                # There's no way to install platform requirements out of band
                # as we're creating the php environment via pre-commit, nor is
                # there a generalized way to install them. If hooks
                # need platform requirements, they should install it themselves
                # in a pre-install composer hook. Therefore, we ignore
                # platform requirements for composer installation.
                (
                    'composer',
                    'install',
                    '--ignore-platform-reqs'
                ) + additional_dependencies
            )


def run_hook(repo_cmd_runner, hook, file_args):
    return xargs(
        (repo_cmd_runner.prefix_dir + hook['entry'],) + tuple(hook['args']),
        file_args,
    )
