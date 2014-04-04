
import contextlib

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure


RVM_ENV = 'rvm_env'


class RubyEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return '. {{prefix}}{0}/bin/activate &&'.format(RVM_ENV)


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    yield RubyEnv(repo_cmd_runner)


def install_environment(repo_cmd_runner):
    # Return immediately if we already have a virtualenv
    if repo_cmd_runner.exists(RVM_ENV):
        return

    with clean_path_on_failure(repo_cmd_runner.path(RVM_ENV)):
        repo_cmd_runner.run(['__rvm-env.sh', '{{prefix}}{0}'.format(RVM_ENV)])
        with in_env(repo_cmd_runner) as env:
            env.run('cd {prefix} && bundle install')


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner) as env:
        return helpers.run_hook(env, hook, file_args)
