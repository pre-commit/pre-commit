from __future__ import unicode_literals

import hashlib
import os

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure
from pre_commit.util import mkdirp
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'docker'


def md5(s):
    m = hashlib.md5()
    m.update(s)
    return m.hexdigest()


def docker_tag(repo_cmd_runner):
    return 'pre-commit-{}'.format(
        md5(os.path.basename(repo_cmd_runner.path()))
    ).lower()


def install_environment(
        repo_cmd_runner,
        version='default',
        additional_dependencies=(),
):
    assert repo_cmd_runner.exists('Dockerfile')
    # I don't know of anybody trying to juggle multiple docker installations
    # so this seems sufficient
    directory = helpers.environment_dir(ENVIRONMENT_DIR, 'default')
    mkdirp(os.path.join(repo_cmd_runner.path(), directory))

    cmd = (
        'docker', 'build', '--pull',
        '--tag', docker_tag(repo_cmd_runner),
        '.'
    )

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup it's state files on failure
    env_dir = repo_cmd_runner.path(directory)
    with clean_path_on_failure(env_dir):
        helpers.run_setup_cmd(repo_cmd_runner, cmd)


def run_hook(repo_cmd_runner, hook, file_args):
    cmd = (
        'docker', 'run',
        '-t',
        '-v', '{}:/src'.format(os.getcwd()),
        '--workdir', '/src',
        docker_tag(repo_cmd_runner)
    )

    return xargs(
        cmd + (hook['entry'],) + tuple(hook['args']), file_args,
    )
