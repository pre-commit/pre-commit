from __future__ import annotations

import builtins
import json
import ntpath
import os.path
import posixpath
from unittest import mock

import pytest

from pre_commit.languages import docker
from pre_commit.util import CalledProcessError
from testing.language_helpers import run_language
from testing.util import xfailif_windows

DOCKER_MOUNTINFO_EXAMPLE = b'''\
510 411 0:60 / / rw,relatime - overlay overlay rw,lowerdir=/var/lib/docker/overlay2/l/OZJBU77BXANIRGNPAKZMM5XPST:/var/lib/docker/overlay2/l/SKTYEQA3QFEMJRGKPIEHDKDDRV,upperdir=/var/lib/docker/overlay2/5210690d97e93f988f6edf91ce417a5e89e34169ed651a816e51ce6e0d66b596/diff,workdir=/var/lib/docker/overlay2/5210690d97e93f988f6edf91ce417a5e89e34169ed651a816e51ce6e0d66b596/work
512 510 0:70 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
513 510 0:87 / /dev rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
514 513 0:88 / /dev/pts rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
515 510 0:89 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs ro
516 515 0:90 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,mode=755,inode64
517 516 0:28 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/systemd ro,nosuid,nodev,noexec,relatime master:11 - cgroup cgroup rw,xattr,name=systemd
518 516 0:31 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/memory ro,nosuid,nodev,noexec,relatime master:15 - cgroup cgroup rw,memory
519 516 0:32 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/pids ro,nosuid,nodev,noexec,relatime master:16 - cgroup cgroup rw,pids
520 516 0:33 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/cpu,cpuacct ro,nosuid,nodev,noexec,relatime master:17 - cgroup cgroup rw,cpu,cpuacct
521 516 0:34 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/perf_event ro,nosuid,nodev,noexec,relatime master:18 - cgroup cgroup rw,perf_event
522 516 0:35 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/hugetlb ro,nosuid,nodev,noexec,relatime master:19 - cgroup cgroup rw,hugetlb
523 516 0:36 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/cpuset ro,nosuid,nodev,noexec,relatime master:20 - cgroup cgroup rw,cpuset
524 516 0:37 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/rdma ro,nosuid,nodev,noexec,relatime master:21 - cgroup cgroup rw,rdma
525 516 0:38 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/net_cls,net_prio ro,nosuid,nodev,noexec,relatime master:22 - cgroup cgroup rw,net_cls,net_prio
526 516 0:39 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/freezer ro,nosuid,nodev,noexec,relatime master:23 - cgroup cgroup rw,freezer
527 516 0:40 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/blkio ro,nosuid,nodev,noexec,relatime master:24 - cgroup
cgroup rw,blkio
528 516 0:41 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/devices ro,nosuid,nodev,noexec,relatime master:25 - cgroup cgroup rw,devices
529 516 0:42 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/misc ro,nosuid,nodev,noexec,relatime master:26 - cgroup cgroup rw,misc
530 513 0:66 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
531 513 0:91 / /dev/shm rw,nosuid,nodev,noexec,relatime - tmpfs shm rw,size=65536k,inode64
532 510 8:2 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/resolv.conf /etc/resolv.conf rw,relatime - ext4 /dev/sda2 rw,errors=remount-ro
533 510 8:2 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/hostname /etc/hostname rw,relatime - ext4 /dev/sda2 rw,errors=remount-ro
534 510 8:2 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/hosts /etc/hosts rw,relatime - ext4 /dev/sda2 rw,errors=remount-ro
535 510 0:22 /docker.sock /run/docker.sock rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,size=2047768k,mode=755,inode64
412 513 0:88 /0 /dev/console rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
413 512 0:70 /bus /proc/bus ro,nosuid,nodev,noexec,relatime - proc proc rw
414 512 0:70 /fs /proc/fs ro,nosuid,nodev,noexec,relatime - proc proc rw
415 512 0:70 /irq /proc/irq ro,nosuid,nodev,noexec,relatime - proc proc rw
416 512 0:70 /sys /proc/sys ro,nosuid,nodev,noexec,relatime - proc proc rw
417 512 0:70 /sysrq-trigger /proc/sysrq-trigger ro,nosuid,nodev,noexec,relatime - proc proc rw
418 512 0:92 / /proc/acpi ro,relatime - tmpfs tmpfs ro,inode64
419 512 0:87 /null /proc/interrupts rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
420 512 0:87 /null /proc/kcore rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
421 512 0:87 /null /proc/keys rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
422 512 0:87 /null /proc/timer_list rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
423 515 0:93 / /sys/firmware ro,relatime - tmpfs tmpfs ro,inode64
'''  # noqa: E501

# The ID should match the above cgroup example.
CONTAINER_ID = 'c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7'  # noqa: E501

NON_DOCKER_MOUNTINFO_EXAMPLE = b'''\
21 27 0:19 / /sys rw,nosuid,nodev,noexec,relatime shared:7 - sysfs sysfs rw
22 27 0:20 / /proc rw,nosuid,nodev,noexec,relatime shared:14 - proc proc rw
23 27 0:5 / /dev rw,nosuid,relatime shared:2 - devtmpfs udev rw,size=10219484k,nr_inodes=2554871,mode=755,inode64
24 23 0:21 / /dev/pts rw,nosuid,noexec,relatime shared:3 - devpts devpts rw,gid=5,mode=620,ptmxmode=000
25 27 0:22 / /run rw,nosuid,nodev,noexec,relatime shared:5 - tmpfs tmpfs rw,size=2047768k,mode=755,inode64
27 1 8:2 / / rw,relatime shared:1 - ext4 /dev/sda2 rw,errors=remount-ro
28 21 0:6 / /sys/kernel/security rw,nosuid,nodev,noexec,relatime shared:8 - securityfs securityfs rw
29 23 0:24 / /dev/shm rw,nosuid,nodev shared:4 - tmpfs tmpfs rw,inode64
30 25 0:25 / /run/lock rw,nosuid,nodev,noexec,relatime shared:6 - tmpfs tmpfs rw,size=5120k,inode64
'''


def test_docker_fallback_user():
    def invalid_attribute():
        raise AttributeError

    with mock.patch.multiple(
            'os', create=True,
            getuid=invalid_attribute,
            getgid=invalid_attribute,
    ):
        assert docker.get_docker_user() == ()


@pytest.fixture(autouse=True)
def _avoid_cache():
    with mock.patch.object(
            docker,
            '_is_rootless',
            docker._is_rootless.__wrapped__,
    ):
        yield


@pytest.mark.parametrize(
    'info_ret',
    (
        (0, b'{"SecurityOptions": ["name=rootless","name=cgroupns"]}', b''),
        (0, b'{"host": {"security": {"rootless": true}}}', b''),
    ),
)
def test_docker_user_rootless(info_ret):
    with mock.patch.object(docker, 'cmd_output_b', return_value=info_ret):
        assert docker.get_docker_user() == ()


@pytest.mark.parametrize(
    'info_ret',
    (
        (0, b'{"SecurityOptions": ["name=cgroupns"]}', b''),
        (0, b'{"host": {"security": {"rootless": false}}}', b''),
        (0, b'{"respone_from_some_other_container_engine": true}', b''),
        (1, b'', b''),
    ),
)
def test_docker_user_non_rootless(info_ret):
    with mock.patch.object(docker, 'cmd_output_b', return_value=info_ret):
        assert docker.get_docker_user() != ()


def test_in_docker_no_file():
    with mock.patch.object(builtins, 'open', side_effect=FileNotFoundError):
        assert docker._is_in_docker() is False


def _mock_open(data):
    return mock.patch.object(
        builtins,
        'open',
        new_callable=mock.mock_open,
        read_data=data,
    )


def test_in_docker_docker_in_file():
    with _mock_open(DOCKER_MOUNTINFO_EXAMPLE):
        assert docker._is_in_docker() is True


def test_in_docker_docker_not_in_file():
    with _mock_open(NON_DOCKER_MOUNTINFO_EXAMPLE):
        assert docker._is_in_docker() is False


def test_get_container_id():
    with _mock_open(DOCKER_MOUNTINFO_EXAMPLE):
        assert docker._get_container_id() == CONTAINER_ID


def test_get_container_id_failure():
    with _mock_open(b''), pytest.raises(RuntimeError):
        docker._get_container_id()


def test_get_docker_path_not_in_docker_returns_same():
    with mock.patch.object(docker, '_is_in_docker', return_value=False):
        assert docker._get_docker_path('abc') == 'abc'


@pytest.fixture
def in_docker():
    with mock.patch.object(docker, '_is_in_docker', return_value=True):
        with mock.patch.object(
            docker, '_get_container_id', return_value=CONTAINER_ID,
        ):
            yield


def _linux_commonpath():
    return mock.patch.object(os.path, 'commonpath', posixpath.commonpath)


def _nt_commonpath():
    return mock.patch.object(os.path, 'commonpath', ntpath.commonpath)


def _docker_output(out):
    ret = (0, out, b'')
    return mock.patch.object(docker, 'cmd_output_b', return_value=ret)


def test_get_docker_path_in_docker_no_binds_same_path(in_docker):
    docker_out = json.dumps([{'Mounts': []}]).encode()

    with _docker_output(docker_out):
        assert docker._get_docker_path('abc') == 'abc'


def test_get_docker_path_in_docker_binds_path_equal(in_docker):
    binds_list = [{'Source': '/opt/my_code', 'Destination': '/project'}]
    docker_out = json.dumps([{'Mounts': binds_list}]).encode()

    with _linux_commonpath(), _docker_output(docker_out):
        assert docker._get_docker_path('/project') == '/opt/my_code'


def test_get_docker_path_in_docker_binds_path_complex(in_docker):
    binds_list = [{'Source': '/opt/my_code', 'Destination': '/project'}]
    docker_out = json.dumps([{'Mounts': binds_list}]).encode()

    with _linux_commonpath(), _docker_output(docker_out):
        path = '/project/test/something'
        assert docker._get_docker_path(path) == '/opt/my_code/test/something'


def test_get_docker_path_in_docker_no_substring(in_docker):
    binds_list = [{'Source': '/opt/my_code', 'Destination': '/project'}]
    docker_out = json.dumps([{'Mounts': binds_list}]).encode()

    with _linux_commonpath(), _docker_output(docker_out):
        path = '/projectSuffix/test/something'
        assert docker._get_docker_path(path) == path


def test_get_docker_path_in_docker_binds_path_many_binds(in_docker):
    binds_list = [
        {'Source': '/something_random', 'Destination': '/not-related'},
        {'Source': '/opt/my_code', 'Destination': '/project'},
        {'Source': '/something-random-2', 'Destination': '/not-related-2'},
    ]
    docker_out = json.dumps([{'Mounts': binds_list}]).encode()

    with _linux_commonpath(), _docker_output(docker_out):
        assert docker._get_docker_path('/project') == '/opt/my_code'


def test_get_docker_path_in_docker_windows(in_docker):
    binds_list = [{'Source': r'c:\users\user', 'Destination': r'c:\folder'}]
    docker_out = json.dumps([{'Mounts': binds_list}]).encode()

    with _nt_commonpath(), _docker_output(docker_out):
        path = r'c:\folder\test\something'
        expected = r'c:\users\user\test\something'
        assert docker._get_docker_path(path) == expected


def test_get_docker_path_in_docker_docker_in_docker(in_docker):
    # won't be able to discover "self" container in true docker-in-docker
    err = CalledProcessError(1, (), b'', b'')
    with mock.patch.object(docker, 'cmd_output_b', side_effect=err):
        assert docker._get_docker_path('/project') == '/project'


@xfailif_windows  # pragma: win32 no cover
def test_docker_hook(tmp_path):
    dockerfile = '''\
FROM ubuntu:22.04
CMD ["echo", "This is overwritten by the entry"']
'''
    tmp_path.joinpath('Dockerfile').write_text(dockerfile)

    ret = run_language(tmp_path, docker, 'echo hello hello world')
    assert ret == (0, b'hello hello world\n')


@xfailif_windows  # pragma: win32 no cover
def test_docker_hook_mount_permissions(tmp_path):
    dockerfile = '''\
FROM ubuntu:22.04
'''
    tmp_path.joinpath('Dockerfile').write_text(dockerfile)

    retcode, _ = run_language(tmp_path, docker, 'touch', ('README.md',))
    assert retcode == 0
