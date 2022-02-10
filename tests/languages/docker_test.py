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

DOCKER_CGROUP_EXAMPLE = b'''\
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

# The ID should match the above cgroup example.
CONTAINER_ID = 'c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7'  # noqa: E501

NON_DOCKER_CGROUP_EXAMPLE = b'''\
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

DOCKER_SCHED_EXAMPLE = b'''\
sh (1, #threads: 1)
-------------------------------------------------------------------
se.exec_start                                :     349708379.385019
se.vruntime                                  :            32.684454
se.sum_exec_runtime                          :            33.860082
se.nr_migrations                             :                   18
nr_switches                                  :                   77
nr_voluntary_switches                        :                   64
nr_involuntary_switches                      :                   13
se.load.weight                               :              1048576
se.avg.load_sum                              :                  198
se.avg.runnable_sum                          :               203813
se.avg.util_sum                              :               200802
se.avg.load_avg                              :                    4
se.avg.runnable_avg                          :                    4
se.avg.util_avg                              :                    4
se.avg.last_update_time                      :      349700175852544
se.avg.util_est.ewma                         :                    8
se.avg.util_est.enqueued                     :                    0
uclamp.min                                   :                    0
uclamp.max                                   :                 1024
effective uclamp.min                         :                    0
effective uclamp.max                         :                 1024
policy                                       :                    0
prio                                         :                  120
clock-delta                                  :                   27
mm->numa_scan_seq                            :                    0
numa_pages_migrated                          :                    0
numa_preferred_nid                           :                   -1
total_numa_faults                            :                    0
current_node=0, numa_group_id=0
numa_faults node=0 task_private=0 task_shared=0 group_private=0 group_shared=0
'''  # noqa: E501

SYSTEMD_SCHED_EXAMPLE = b'''\
systemd (1, #threads: 1)
-------------------------------------------------------------------
se.exec_start                                :     349429286.842224
se.vruntime                                  :          2759.778972
se.sum_exec_runtime                          :          9858.995771
se.nr_migrations                             :                11801
nr_switches                                  :                80235
nr_voluntary_switches                        :                78822
nr_involuntary_switches                      :                 1413
se.load.weight                               :              1048576
se.avg.load_sum                              :                 4221
se.avg.runnable_sum                          :              4325517
se.avg.util_sum                              :              3881112
se.avg.load_avg                              :                   91
se.avg.runnable_avg                          :                   91
se.avg.util_avg                              :                   81
se.avg.last_update_time                      :      349418325520384
se.avg.util_est.ewma                         :                   81
se.avg.util_est.enqueued                     :                   81
uclamp.min                                   :                    0
uclamp.max                                   :                 1024
effective uclamp.min                         :                    0
effective uclamp.max                         :                 1024
policy                                       :                    0
prio                                         :                  120
clock-delta                                  :                   78
mm->numa_scan_seq                            :                    0
numa_pages_migrated                          :                    0
numa_preferred_nid                           :                   -1
total_numa_faults                            :                    0
current_node=0, numa_group_id=0
numa_faults node=0 task_private=0 task_shared=0 group_private=0 group_shared=0
'''  # noqa: E501

INIT_SCHED_EXAMPLE = b'''\
init (1, #threads: 1)
-------------------------------------------------------------------
se.exec_start                                :         45362.204529
se.vruntime                                  :         14424.583092
se.sum_exec_runtime                          :           636.475090
se.nr_migrations                             :                    0
nr_switches                                  :                  409
nr_voluntary_switches                        :                  206
nr_involuntary_switches                      :                  203
se.load.weight                               :              1048576
se.runnable_weight                           :              1048576
se.avg.load_sum                              :                   48
se.avg.runnable_load_sum                     :                   48
se.avg.util_sum                              :                37888
se.avg.load_avg                              :                    0
se.avg.runnable_load_avg                     :                    0
se.avg.util_avg                              :                    0
se.avg.last_update_time                      :          45362203648
se.avg.util_est.ewma                         :                    9
se.avg.util_est.enqueued                     :                    0
policy                                       :                    0
prio                                         :                  120
clock-delta                                  :                  396
mm->numa_scan_seq                            :                    0
numa_pages_migrated                          :                    0
numa_preferred_nid                           :                   -1
total_numa_faults                            :                    0
current_node=0, numa_group_id=0
numa_faults node=0 task_private=0 task_shared=0 group_private=0 group_shared=0
'''  # noqa: E501


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
    with _mock_open(DOCKER_CGROUP_EXAMPLE):
        assert docker._is_in_docker_cgroup() is True


def test_in_docker_docker_not_in_file():
    with _mock_open(NON_DOCKER_CGROUP_EXAMPLE):
        assert docker._is_in_docker_cgroup() is False


def test_in_docker_inside_container():
    with _mock_open(DOCKER_SCHED_EXAMPLE):
        assert docker._is_in_docker_sched() is True


def test_in_docker_outside_container_systemd():
    with _mock_open(SYSTEMD_SCHED_EXAMPLE):
        assert docker._is_in_docker_sched() is False


def test_in_docker_outside_container_init():
    with _mock_open(INIT_SCHED_EXAMPLE):
        assert docker._is_in_docker_sched() is False


def test_get_container_id():
    with _mock_open(DOCKER_CGROUP_EXAMPLE):
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
    err = CalledProcessError(1, (), 0, b'', b'')
    with mock.patch.object(docker, 'cmd_output_b', side_effect=err):
        assert docker._get_docker_path('/project') == '/project'
