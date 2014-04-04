import contextlib

from pre_commit.languages import helpers
from pre_commit.languages import python
from pre_commit.prefixed_command_runner import CalledProcessError
from pre_commit.util import clean_path_on_failure


ENVIRONMENT_DIR = 'node_env'


class NodeEnv(python.PythonEnv):
    @property
    def env_prefix(self):
        base = super(NodeEnv, self).env_prefix
        return ' '.join([
            base,
            '. {{prefix}}{0}/bin/activate &&'.format(ENVIRONMENT_DIR)]
        )


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    yield NodeEnv(repo_cmd_runner)


def install_environment(repo_cmd_runner):
    assert repo_cmd_runner.exists('package.json')

    with clean_path_on_failure(repo_cmd_runner.path(python.ENVIRONMENT_DIR)):
        repo_cmd_runner.run(
            ['virtualenv', '{{prefix}}{0}'.format(python.ENVIRONMENT_DIR)],
        )

        with python.in_env(repo_cmd_runner) as python_env:
            python_env.run('pip install nodeenv')

            with clean_path_on_failure(repo_cmd_runner.path(ENVIRONMENT_DIR)):
                # Try and use the system level node executable first
                try:
                    python_env.run(
                        'nodeenv -n system {{prefix}}{0}'.format(ENVIRONMENT_DIR),
                    )
                except CalledProcessError:
                    # TODO: log failure here
                    # cleanup
                    # TODO: local.path(ENVIRONMENT_DIR).delete()
                    python_env.run(
                        'nodeenv --jobs 4 {{prefix}}{0}'.format(ENVIRONMENT_DIR),
                    )

                with in_env(repo_cmd_runner) as node_env:
                    node_env.run('cd {prefix} && npm install -g')


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner) as env:
        return helpers.run_hook(env, hook, file_args)
