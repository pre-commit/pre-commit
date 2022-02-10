from __future__ import annotations

import hashlib
import json
import os
from typing import Sequence

import pre_commit.constants as C
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'docker'
PRE_COMMIT_LABEL = 'PRE_COMMIT'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def _is_in_docker_cgroup() -> bool:
    try:
        with open('/proc/1/cgroup', 'rb') as f:
            for line in f.readlines():
                if b'docker' in line:
                    break
                else:
                    _, name, path = line.strip().split(b':')
                    if name == b'cpuset' and len(os.path.basename(path)) == 64:
                        break
            else:
                return False

            return True
    except FileNotFoundError:
        return False


def _is_in_docker_sched() -> bool:
    try:
        with open('/proc/1/sched', 'rb') as f:
            line = f.readline()

            if line.startswith(b'systemd ') or line.startswith(b'init '):
                return False

            return True
    except FileNotFoundError:
        return False


def _is_in_docker() -> bool:
    if _is_in_docker_cgroup() or _is_in_docker_sched():
        return True

    return False


def _get_container_id_cgroup() -> str:
    # It's assumed that we already check /proc/1/cgroup in _is_in_docker. The
    # cpuset cgroup controller existed since cgroups were introduced so this
    # way of getting the container ID is pretty reliable.
    with open('/proc/1/cgroup', 'rb') as f:
        for line in f.readlines():
            if line.split(b':')[1] == b'cpuset':
                return os.path.basename(line.split(b':')[2]).strip().decode()

    return ''


def _get_container_id_sched() -> str:
    # The idea here is to try to match the the workdir option found in the
    # overlay mount with the GraphDriver.Data.WorkDir from the docker describe.

    # Get details for the overlay mount type
    try:
        _, out, _ = cmd_output_b('mount', '-t', 'overlay')
    except CalledProcessError:
        # No mount command available or the -t option is not supported
        return ''

    lines = out.decode().strip().split('\n')

    # There is always only one overlay mount inside the container
    if len(lines) > 1 or lines[0] == '' or '(' not in lines[0]:
        return ''

    _, all_opts = lines[0].strip(')').split('(')
    opts = all_opts.split(',')

    # Search for workdir option
    for opt in opts:
        if '=' in opt:
            k, v = opt.split('=')

            if k == 'workdir':
                # We have found workdir
                workdir = v

                break
    else:
        # No workdir was found
        return ''

    # Get list IDs for all running containers
    try:
        _, out, _ = cmd_output_b('docker', 'ps', '--format', '{{ .ID }}')
    except CalledProcessError:
        # There is probably no docker command
        return ''

    container_ids = out.decode().strip().split('\n')

    # Check if there are any container IDs
    if len(container_ids) == 1 and container_ids[0] == '':
        return ''

    # Search for a container that has the workdir we got from the mount command
    for container_id in container_ids:
        try:
            _, out, _ = cmd_output_b('docker', 'inspect', container_id)
        except CalledProcessError:
            # Container probably doesn't exist anymore
            return ''

        container, = json.loads(out)

        if (
                'GraphDriver' in container and
                'Data' in container['GraphDriver'] and
                'WorkDir' in container['GraphDriver']['Data'] and
                container['GraphDriver']['Data']['WorkDir'] == workdir
        ):
            # We have found matching container!
            return container_id
    else:
        # No matching container found
        return ''


def _get_container_id() -> str:
    container_id = _get_container_id_cgroup()

    if container_id == '':
        container_id = _get_container_id_sched()

        if container_id == '':
            raise RuntimeError('Failed to find the container ID.')

    return container_id


def _get_docker_path(path: str) -> str:
    if not _is_in_docker():
        return path

    container_id = _get_container_id()

    try:
        _, out, _ = cmd_output_b('docker', 'inspect', container_id)
    except CalledProcessError:
        # self-container was not visible from here (perhaps docker-in-docker)
        return path

    container, = json.loads(out)
    for mount in container['Mounts']:
        src_path = mount['Source']
        to_path = mount['Destination']
        if os.path.commonpath((path, to_path)) == to_path:
            # So there is something in common,
            # and we can proceed remapping it
            return path.replace(to_path, src_path)
    # we're in Docker, but the path is not mounted, cannot really do anything,
    # so fall back to original path
    return path


def md5(s: str) -> str:  # pragma: win32 no cover
    return hashlib.md5(s.encode()).hexdigest()


def docker_tag(prefix: Prefix) -> str:  # pragma: win32 no cover
    md5sum = md5(os.path.basename(prefix.prefix_dir)).lower()
    return f'pre-commit-{md5sum}'


def build_docker_image(
        prefix: Prefix,
        *,
        pull: bool,
) -> None:  # pragma: win32 no cover
    cmd: tuple[str, ...] = (
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
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:  # pragma: win32 no cover
    helpers.assert_version_default('docker', version)
    helpers.assert_no_additional_deps('docker', additional_dependencies)

    directory = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, C.DEFAULT),
    )

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup its state files on failure
    with clean_path_on_failure(directory):
        build_docker_image(prefix, pull=True)
        os.mkdir(directory)


def get_docker_user() -> tuple[str, ...]:  # pragma: win32 no cover
    try:
        return ('-u', f'{os.getuid()}:{os.getgid()}')
    except AttributeError:
        return ()


def docker_cmd() -> tuple[str, ...]:  # pragma: win32 no cover
    return (
        'docker', 'run',
        '--rm',
        *get_docker_user(),
        # https://docs.docker.com/engine/reference/commandline/run/#mount-volumes-from-container-volumes-from
        # The `Z` option tells Docker to label the content with a private
        # unshared label. Only the current container can use a private volume.
        '-v', f'{_get_docker_path(os.getcwd())}:/src:rw,Z',
        '--workdir', '/src',
    )


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> tuple[int, bytes]:  # pragma: win32 no cover
    # Rebuild the docker image in case it has gone missing, as many people do
    # automated cleanup of docker images.
    build_docker_image(hook.prefix, pull=False)

    entry_exe, *cmd_rest = hook.cmd

    entry_tag = ('--entrypoint', entry_exe, docker_tag(hook.prefix))
    cmd = (*docker_cmd(), *entry_tag, *cmd_rest)
    return helpers.run_xargs(hook, cmd, file_args, color=color)
