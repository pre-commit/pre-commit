import builtins
import json
import ntpath
import os.path
import posixpath
from unittest import mock

import pytest

from pre_commit.languages import docker


def test_docker_fallback_user():
    def invalid_attribute():
        raise AttributeError

    with mock.patch.multiple(
            'os', create=True,
            getuid=invalid_attribute,
            getgid=invalid_attribute,
    ):
        assert docker.get_docker_user() == ()


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
    docker_cgroup_example = b'''\
12:hugetlb:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
11:blkio:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
10:freezer:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
9:cpu,cpuacct:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
8:pids:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
7:rdma:/
6:net_cls,net_prio:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
5:cpuset:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
4:devices:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
3:memory:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
2:perf_event:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
1:name=systemd:/docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7
0::/system.slice/containerd.service
'''  # noqa: E501
    with _mock_open(docker_cgroup_example):
        assert docker._is_in_docker() is True


def test_in_docker_docker_not_in_file():
    non_docker_cgroup_example = b'''\
12:perf_event:/
11:hugetlb:/
10:devices:/
9:blkio:/
8:rdma:/
7:cpuset:/
6:cpu,cpuacct:/
5:freezer:/
4:memory:/
3:pids:/
2:net_cls,net_prio:/
1:name=systemd:/init.scope
0::/init.scope
'''
    with _mock_open(non_docker_cgroup_example):
        assert docker._is_in_docker() is False


def test_get_docker_path_not_in_docker_returns_same():
    with mock.patch.object(docker, '_is_in_docker', return_value=False):
        assert docker._get_docker_path('abc') == 'abc'


@pytest.fixture
def in_docker():
    with mock.patch.object(docker, '_is_in_docker', return_value=True):
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
