from __future__ import unicode_literals

import contextlib
import os.path

from pre_commit import git
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'golangenv'


def get_env_patch(venv):  # pragma: windows no cover
    return (
        ('PATH', (os.path.join(venv, 'bin'), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(repo_cmd_runner):  # pragma: windows no cover
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


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):  # pragma: windows no cover
    helpers.assert_version_default('golang', version)
    helpers.assert_no_additional_deps('golang', additional_dependencies)
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


def run_hook(repo_cmd_runner, hook, file_args):  # pragma: windows no cover
    with in_env(repo_cmd_runner):
        return xargs(helpers.to_cmd(hook), file_args)
