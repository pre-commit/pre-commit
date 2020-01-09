import hashlib
import os

import pre_commit.constants as C
from pre_commit import five
from pre_commit.languages import helpers
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output_b


ENVIRONMENT_DIR = 'docker'
PRE_COMMIT_LABEL = 'PRE_COMMIT'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def md5(s):  # pragma: windows no cover
    return hashlib.md5(five.to_bytes(s)).hexdigest()


def docker_tag(prefix):  # pragma: windows no cover
    md5sum = md5(os.path.basename(prefix.prefix_dir)).lower()
    return f'pre-commit-{md5sum}'


def docker_is_running():  # pragma: windows no cover
    try:
        cmd_output_b('docker', 'ps')
    except CalledProcessError:
        return False
    else:
        return True


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
        helpers.environment_dir(ENVIRONMENT_DIR, C.DEFAULT),
    )

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup its state files on failure
    with clean_path_on_failure(directory):
        build_docker_image(prefix, pull=True)
        os.mkdir(directory)


def get_docker_user():  # pragma: windows no cover
    try:
        return '{}:{}'.format(os.getuid(), os.getgid())
    except AttributeError:
        return '1000:1000'


def docker_cmd():  # pragma: windows no cover
    return (
        'docker', 'run',
        '--rm',
        '-u', get_docker_user(),
        # https://docs.docker.com/engine/reference/commandline/run/#mount-volumes-from-container-volumes-from
        # The `Z` option tells Docker to label the content with a private
        # unshared label. Only the current container can use a private volume.
        '-v', '{}:/src:rw,Z'.format(os.getcwd()),
        '--workdir', '/src',
    )


def run_hook(hook, file_args, color):  # pragma: windows no cover
    assert_docker_available()
    # Rebuild the docker image in case it has gone missing, as many people do
    # automated cleanup of docker images.
    build_docker_image(hook.prefix, pull=False)

    hook_cmd = hook.cmd
    entry_exe, cmd_rest = hook.cmd[0], hook_cmd[1:]

    entry_tag = ('--entrypoint', entry_exe, docker_tag(hook.prefix))
    cmd = docker_cmd() + entry_tag + cmd_rest
    return helpers.run_xargs(hook, cmd, file_args, color=color)
