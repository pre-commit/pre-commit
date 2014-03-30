import contextlib
import subprocess

from pre_commit.languages import helpers
from pre_commit.languages import python


NODE_ENV = 'node_env'


class NodeEnv(python.PythonEnv):
    @property
    def env_prefix(self):
        base = super(NodeEnv, self).env_prefix
        return ' '.join([
            base,
            '. {{prefix}}{0}/bin/activate &&'.format(NODE_ENV)]
        )


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    yield NodeEnv(repo_cmd_runner)


def install_environment(repo_cmd_runner):
    assert repo_cmd_runner.exists('package.json')

    # Return immediately if we already have a virtualenv
    if repo_cmd_runner.exists(NODE_ENV):
        return

    repo_cmd_runner.run(['virtualenv', '{{prefix}}{0}'.format(python.PY_ENV)])

    with python.in_env(repo_cmd_runner) as python_env:
        python_env.run('pip install nodeenv')

        # Try and use the system level node executable first
        try:
            python_env.run('nodeenv -n system {{prefix}}{0}'.format(NODE_ENV))
        except subprocess.CalledProcessError:
            # TODO: log failure here
            # cleanup
            # TODO: local.path(NODE_ENV).delete()
            python_env.run('nodeenv --jobs 4 {{prefix}}{0}'.format(NODE_ENV))

        with in_env(repo_cmd_runner) as node_env:
            node_env.run('cd {prefix} && npm install -g')


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner) as env:
        return helpers.run_hook(env, hook, file_args)
