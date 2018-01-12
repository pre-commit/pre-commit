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


def docker_tag(prefix):  # pragma: windows no cover
    md5sum = md5(os.path.basename(prefix.prefix_dir)).lower()
    return 'pre-commit-{}'.format(md5sum)


def docker_is_running():  # pragma: windows no cover
    try:
        return cmd_output('docker', 'ps')[0] == 0
    except CalledProcessError:
        return False


def assert_docker_available():  # pragma: windows no cover
    assert docker_is_running(), (
        'Docker is either not running or not configured in this environment'
    )


def build_docker_image(prefix, **kwargs):  # pragma: windows no cover
    pull = kwargs.pop('pull')
    assert not kwargs, kwargs
    cmd = (
        'docker', 'build',
        '--tag', docker_tag(prefix),
        '--label', PRE_COMMIT_LABEL,
    )
    if pull:
        cmd += ('--pull',)
    # This must come last for old versions of docker.  See #477
    cmd += ('.',)
    helpers.run_setup_cmd(prefix, cmd)


def install_environment(
        prefix, version, additional_dependencies,
):  # pragma: windows no cover
    helpers.assert_version_default('docker', version)
    helpers.assert_no_additional_deps('docker', additional_dependencies)
    assert_docker_available()

    directory = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, 'default'),
    )

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup it's state files on failure
    with clean_path_on_failure(directory):
        build_docker_image(prefix, pull=True)
        os.mkdir(directory)


def docker_cmd():
    return (
        'docker', 'run',
        '--rm',
        '-u', '{}:{}'.format(os.getuid(), os.getgid()),
        # https://docs.docker.com/engine/reference/commandline/run/#mount-volumes-from-container-volumes-from
        # The `Z` option tells Docker to label the content with a private
        # unshared label. Only the current container can use a private volume.
        '-v', '{}:/src:rw,Z'.format(os.getcwd()),
        '--workdir', '/src',
    )


def run_hook(prefix, hook, file_args):  # pragma: windows no cover
    assert_docker_available()
    # Rebuild the docker image in case it has gone missing, as many people do
    # automated cleanup of docker images.
    build_docker_image(prefix, pull=False)

    hook_cmd = helpers.to_cmd(hook)
    entry_exe, cmd_rest = hook_cmd[0], hook_cmd[1:]

    entry_tag = ('--entrypoint', entry_exe, docker_tag(prefix))
    cmd = docker_cmd() + entry_tag + cmd_rest
    return xargs(cmd, file_args)
