from __future__ import unicode_literals

import contextlib
import sys

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure


ENVIRONMENT_DIR = 'node_env'


class NodeEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return ". '{{prefix}}{0}/bin/activate' &&".format(
            helpers.environment_dir(ENVIRONMENT_DIR, self.language_version),
        )


@contextlib.contextmanager
def in_env(repo_cmd_runner, language_version):
    yield NodeEnv(repo_cmd_runner, language_version)


def install_environment(repo_cmd_runner, version='default'):
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

        with in_env(repo_cmd_runner, version) as node_env:
            node_env.run("cd '{prefix}' && npm install -g")


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner, hook['language_version']) as env:
        return helpers.run_hook(env, hook, file_args)
