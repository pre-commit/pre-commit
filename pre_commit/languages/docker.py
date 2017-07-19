from __future__ import absolute_import
from __future__ import unicode_literals

import hashlib
import os

from pre_commit import five
from pre_commit.languages import helpers
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'docker'
PRE_COMMIT_LABEL = 'PRE_COMMIT'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def md5(s):  # pragma: windows no cover
    return hashlib.md5(five.to_bytes(s)).hexdigest()


def docker_tag(repo_cmd_runner):  # pragma: windows no cover
    return 'pre-commit-{}'.format(
        md5(os.path.basename(repo_cmd_runner.path())),
    ).lower()


def docker_is_running():  # pragma: windows no cover
    try:
        return cmd_output('docker', 'ps')[0] == 0
    except CalledProcessError:
        return False


def assert_docker_available():  # pragma: windows no cover
    assert docker_is_running(), (
        'Docker is either not running or not configured in this environment'
    )


def build_docker_image(repo_cmd_runner, **kwargs):  # pragma: windows no cover
    pull = kwargs.pop('pull')
    assert not kwargs, kwargs
    cmd = (
        'docker', 'build',
        '--tag', docker_tag(repo_cmd_runner),
        '--label', PRE_COMMIT_LABEL,
    )
    if pull:
        cmd += ('--pull',)
    # This must come last for old versions of docker.  See #477
    cmd += ('.',)
    helpers.run_setup_cmd(repo_cmd_runner, cmd)


def install_environment(
        repo_cmd_runner, version, additional_dependencies,
):  # pragma: windows no cover
    assert repo_cmd_runner.exists('Dockerfile'), (
        'No Dockerfile was found in the hook repository'
    )
    helpers.assert_version_default('docker', version)
    helpers.assert_no_additional_deps('docker', additional_dependencies)
    assert_docker_available()

    directory = repo_cmd_runner.path(
        helpers.environment_dir(ENVIRONMENT_DIR, 'default'),
    )

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup it's state files on failure
    with clean_path_on_failure(directory):
        build_docker_image(repo_cmd_runner, pull=True)
        os.mkdir(directory)


def run_hook(repo_cmd_runner, hook, file_args):  # pragma: windows no cover
    assert_docker_available()
    # Rebuild the docker image in case it has gone missing, as many people do
    # automated cleanup of docker images.
    build_docker_image(repo_cmd_runner, pull=False)

    hook_cmd = helpers.to_cmd(hook)
    entry_executable, cmd_rest = hook_cmd[0], hook_cmd[1:]

    cmd = (
        'docker', 'run',
        '--rm',
        '-u', '{}:{}'.format(os.getuid(), os.getgid()),
        '-v', '{}:/src:rw'.format(os.getcwd()),
        '--workdir', '/src',
        '--entrypoint', entry_executable,
        docker_tag(repo_cmd_runner),
    ) + cmd_rest

    return xargs(cmd, file_args)
