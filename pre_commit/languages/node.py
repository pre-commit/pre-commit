from __future__ import unicode_literals

import contextlib
import sys

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure


ENVIRONMENT_DIR = 'node_env'


class NodeEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return '. {{prefix}}{0}/bin/activate &&'.format(ENVIRONMENT_DIR)


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    yield NodeEnv(repo_cmd_runner)


def install_environment(repo_cmd_runner, version='default'):
    assert repo_cmd_runner.exists('package.json')

    env_dir = repo_cmd_runner.path(ENVIRONMENT_DIR)
    with clean_path_on_failure(env_dir):
        cmd = [
            sys.executable, '-m', 'nodeenv', '--prebuilt',
            '{{prefix}}{0}'.format(ENVIRONMENT_DIR),
        ]

        if version != 'default':
            cmd.extend(['-n', version])

        repo_cmd_runner.run(cmd)

        with in_env(repo_cmd_runner) as node_env:
            node_env.run('cd {prefix} && npm install -g')


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner) as env:
        return helpers.run_hook(env, hook, file_args)
