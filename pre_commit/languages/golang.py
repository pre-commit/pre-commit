from __future__ import unicode_literals

import contextlib
import os.path

from pre_commit import git
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.util import rmtree
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'golangenv'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def get_env_patch(venv):
    return (
        ('PATH', (os.path.join(venv, 'bin'), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    envdir = repo_cmd_runner.path(
        helpers.environment_dir(ENVIRONMENT_DIR, 'default'),
    )
    with envcontext(get_env_patch(envdir)):
        yield


def guess_go_dir(remote_url):
    if remote_url.endswith('.git'):
        remote_url = remote_url[:-1 * len('.git')]
    remote_url = remote_url.replace(':', '/')
    looks_like_url = '//' in remote_url or '@' in remote_url
    if looks_like_url:
        _, _, remote_url = remote_url.rpartition('//')
        _, _, remote_url = remote_url.rpartition('@')
        return remote_url
    else:
        return 'unknown_src_dir'


def install_environment(repo_cmd_runner, version, additional_dependencies):
    helpers.assert_version_default('golang', version)
    directory = repo_cmd_runner.path(
        helpers.environment_dir(ENVIRONMENT_DIR, 'default'),
    )

    with clean_path_on_failure(directory):
        remote = git.get_remote_url(repo_cmd_runner.path())
        repo_src_dir = os.path.join(directory, 'src', guess_go_dir(remote))

        # Clone into the goenv we'll create
        helpers.run_setup_cmd(
            repo_cmd_runner, ('git', 'clone', '.', repo_src_dir),
        )

        env = dict(os.environ, GOPATH=directory)
        cmd_output('go', 'get', './...', cwd=repo_src_dir, env=env)
        for dependency in additional_dependencies:
            cmd_output('go', 'get', dependency, cwd=repo_src_dir, env=env)
        # Same some disk space, we don't need these after installation
        rmtree(repo_cmd_runner.path(directory, 'src'))
        rmtree(repo_cmd_runner.path(directory, 'pkg'))


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner):
        return xargs(helpers.to_cmd(hook), file_args)
