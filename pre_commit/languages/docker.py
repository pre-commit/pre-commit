from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.prefix import Prefix
from pre_commit.util import CalledProcessError
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'docker'
PRE_COMMIT_LABEL = 'PRE_COMMIT'
get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
in_env = lang_base.no_env  # no special environment for docker


def _is_in_docker() -> bool:
    """Determine if we're running inside a docker container.

    Uses multiple detection methods:
    1. Check for "docker" in /proc/1/cgroup (cgroups v1)
    2. Check /proc/self/mountinfo for container indicators
    3. Check for /.dockerenv file existence
    4. Check for IS_CONTAINER environment variable
    """
    # Method 1 (cgroups v1): Check /proc/1/cgroup
    try:
        with open("/proc/1/cgroup", "rb") as f:
            cgroup_content = f.read()
            if b"docker" in cgroup_content or b"containerd" in cgroup_content:
                return True
    except FileNotFoundError:
        pass

    # Method 2 (cgroups v2): Check /proc/self/mountinfo for container indicators
    try:
        with open("/proc/self/mountinfo", "rb") as f:
            mountinfo = f.read()
            if b"overlay" in mountinfo and (b"docker" in mountinfo or b"containerd" in mountinfo):
                return True
    except FileNotFoundError:
        pass

    # Method 3: Check for /.dockerenv file
    if os.path.exists("/.dockerenv"):
        return True

    # Method 4: Check for IS_CONTAINER environment variable
    if os.environ.get("IS_CONTAINER"):
        return True

    return False


def _get_container_id() -> str:
    # Method 1 (cgroups v1): Parse /proc/1/cgroup
    try:
        with open('/proc/1/cgroup', 'rb') as f:
            for line in f.readlines():
                if line.split(b':')[1] == b'cpuset':
                    return os.path.basename(line.split(b':')[2]).strip().decode()
    except (FileNotFoundError, IndexError, ValueError):
        pass

    # Method 2 (cgroups v2): Parse /proc/self/mountinfo
    try:
        with open('/proc/self/mountinfo', 'rb') as f:
            for line in f.readlines():
                if b'/docker/containers/' in line:
                    parts = line.split(b'/docker/containers/')
                    if len(parts) >= 2:
                        container_id = parts[1].split(b'/')[0].decode()
                        if container_id:
                            return container_id
    except (FileNotFoundError, IndexError):
        pass

    raise RuntimeError('Failed to find the container ID in either /proc/1/cgroup or /proc/self/mountinfo.')


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
    lang_base.setup_cmd(prefix, cmd)


def install_environment(
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:  # pragma: win32 no cover
    lang_base.assert_version_default('docker', version)
    lang_base.assert_no_additional_deps('docker', additional_dependencies)

    directory = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)

    # Docker doesn't really have relevant disk environment, but pre-commit
    # still needs to cleanup its state files on failure
    build_docker_image(prefix, pull=True)
    os.mkdir(directory)


def get_docker_user() -> tuple[str, ...]:  # pragma: win32 no cover
    try:
        return ('-u', f'{os.getuid()}:{os.getgid()}')
    except AttributeError:
        return ()


def get_docker_tty(*, color: bool) -> tuple[str, ...]:  # pragma: win32 no cover  # noqa: E501
    return (('--tty',) if color else ())


def docker_cmd(*, color: bool) -> tuple[str, ...]:  # pragma: win32 no cover
    return (
        'docker', 'run',
        '--rm',
        *get_docker_tty(color=color),
        *get_docker_user(),
        # https://docs.docker.com/engine/reference/commandline/run/#mount-volumes-from-container-volumes-from
        # The `Z` option tells Docker to label the content with a private
        # unshared label. Only the current container can use a private volume.
        '-v', f'{_get_docker_path(os.getcwd())}:/src:rw,Z',
        '--workdir', '/src',
    )


def run_hook(
        prefix: Prefix,
        entry: str,
        args: Sequence[str],
        file_args: Sequence[str],
        *,
        is_local: bool,
        require_serial: bool,
        color: bool,
) -> tuple[int, bytes]:  # pragma: win32 no cover
    # Rebuild the docker image in case it has gone missing, as many people do
    # automated cleanup of docker images.
    build_docker_image(prefix, pull=False)

    entry_exe, *cmd_rest = lang_base.hook_cmd(entry, args)

    entry_tag = ('--entrypoint', entry_exe, docker_tag(prefix))
    return lang_base.run_xargs(
        (*docker_cmd(color=color), *entry_tag, *cmd_rest),
        file_args,
        require_serial=require_serial,
        color=color,
    )
