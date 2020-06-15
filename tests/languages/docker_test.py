from unittest import mock

from pre_commit.languages import docker
from pre_commit.util import CalledProcessError

DOCKER_NOT_ROOTLESS_SYSTEM_INFO = '''
Client:
 Debug Mode: false

Server:
 Containers: 8
  Running: 0
  Paused: 0
  Stopped: 8
 Images: 2
 Server Version: 19.03.8
 Storage Driver: overlay2
  Backing Filesystem: <unknown>
  Supports d_type: true
  Native Overlay Diff: true
 Logging Driver: journald
 Cgroup Driver: systemd
 Plugins:
  Volume: local
  Network: bridge host ipvlan macvlan null overlay
  Log: awslogs fluentd gcplogs gelf journald json-file local logentries splunk syslog
 Swarm: inactive
 Runtimes: runc
 Default Runtime: runc
 Init Binary: /usr/libexec/docker/docker-init
 containerd version:
 runc version: fbdbaf85ecbc0e077f336c03062710435607dbf1
 init version:
 Security Options:
  seccomp
   Profile: default
  selinux
 Kernel Version: 5.6.14-300.fc32.x86_64
 Operating System: Fedora 32 (Thirty Two)
 OSType: linux
 Architecture: x86_64
 CPUs: 8
 Total Memory: 15.29GiB
 Name: carbon
 ID: IUGE:4L5B:VVTV:JGIA:IIJN:G7MG:TVGF:XBVW:YHF7:MYRK:L524:4HBK
 Docker Root Dir: /var/lib/docker
 Debug Mode: false
 Registry: https://index.docker.io/v1/
 Labels:
 Experimental: false
 Insecure Registries:
  127.0.0.0/8
 Live Restore Enabled: true
'''  # noqa

DOCKER_ROOTLESS_SYSTEM_INFO = '''
Client:
 Debug Mode: false

Server:
 Containers: 0
  Running: 0
  Paused: 0
  Stopped: 0
 Images: 0
 Server Version: 19.03.11
 Storage Driver: vfs
 Logging Driver: json-file
 Cgroup Driver: none
 Plugins:
  Volume: local
  Network: bridge host ipvlan macvlan null overlay
  Log: awslogs fluentd gcplogs gelf journald json-file local logentries splunk syslog
 Swarm: inactive
 Runtimes: runc
 Default Runtime: runc
 Init Binary: docker-init
 containerd version: 7ad184331fa3e55e52b890ea95e65ba581ae3429
 runc version: dc9208a3303feef5b3839f4323d9beb36df0a9dd
 init version: fec3683
 Security Options:
  seccomp
   Profile: default
  rootless
 Kernel Version: 5.6.16-300.fc32.x86_64
 Operating System: Fedora 32 (Workstation Edition)
 OSType: linux
 Architecture: x86_64
 CPUs: 8
 Total Memory: 23.36GiB
 Name: laptop.centsix.taz
 ID: 6EMS:RSJ4:NXM3:3D56:CV4N:VEUX:LBFM:KWHK:P7XA:HTCS:GVSC:UVUE
 Docker Root Dir: /home/remote/user/.local/share/docker
 Debug Mode: false
 Registry: https://index.docker.io/v1/
 Labels:
 Experimental: true
 Insecure Registries:
  127.0.0.0/8
 Live Restore Enabled: false
 Product License: Community Engine
'''  # noqa

PODMAN_SYSTEM_INFO = '''
host:
  arch: amd64
  buildahVersion: 1.14.9
  cgroupVersion: v2
  conmon:
    package: conmon-2.0.17-1.fc32.x86_64
    path: /usr/libexec/crio/conmon
    version: 'conmon version 2.0.17, commit: bb8e273f5925c1a51737644637ef65d094a67ab1'
  cpus: 8
  distribution:
    distribution: fedora
    version: "32"
  eventLogger: file
  hostname: laptop.centsix.taz
  idMappings:
    gidmap:
    - container_id: 0
      host_id: 1001
      size: 1
    - container_id: 1
      host_id: 200000
      size: 65536
    uidmap:
    - container_id: 0
      host_id: 105971
      size: 1
    - container_id: 1
      host_id: 200000
      size: 65536
  kernel: 5.6.16-300.fc32.x86_64
  memFree: 7256297472
  memTotal: 25081421824
  ociRuntime:
    name: crun
    package: crun-0.13-2.fc32.x86_64
    path: /usr/bin/crun
    version: |-
      crun version 0.13
      commit: e79e4de4ac16da0ce48777afb72c6241de870525
      spec: 1.0.0
      +SYSTEMD +SELINUX +APPARMOR +CAP +SECCOMP +EBPF +YAJL
  os: linux
  rootless: true
  slirp4netns:
    executable: /usr/bin/slirp4netns
    package: slirp4netns-1.0.0-1.fc32.x86_64
    version: |-
      slirp4netns version 1.0.0
      commit: a3be729152a33e692cd28b52f664defbf2e7810a
      libslirp: 4.2.0
  swapFree: 20372766720
  swapTotal: 20372766720
  uptime: 4h 46m 1.38s (Approximately 0.17 days)
registries: {}
store:
  configFile: /home/remote/user/.config/containers/storage.conf
  containerStore:
    number: 66
    paused: 0
    running: 0
    stopped: 66
  graphDriverName: overlay
  graphOptions:
    overlay.mount_program:
      Executable: /usr/bin/fuse-overlayfs
      Package: fuse-overlayfs-1.0.0-1.fc32.x86_64
      Version: |-
        fusermount3 version: 3.9.1
        fuse-overlayfs: version 1.0.0
        FUSE library version 3.9.1
        using FUSE kernel interface version 7.31
  graphRoot: /home/remote/user/.local/share/containers/storage
  graphStatus:
    Backing Filesystem: extfs
    Native Overlay Diff: "false"
    Supports d_type: "true"
    Using metacopy: "false"
  imageStore:
    number: 23
  runRoot: /tmp/105971
  volumePath: /home/remote/user/.local/share/containers/storage/volumes
'''  # noqa


def test_docker_is_running_process_error():
    with mock.patch(
        'pre_commit.languages.docker.cmd_output_b',
        side_effect=CalledProcessError(1, (), 0, b'', None),
    ):
        assert docker.docker_is_running() is False


def test_docker_fallback_user():
    def invalid_attribute():
        raise AttributeError
    with mock.patch.multiple(
        'os', create=True,
        getuid=invalid_attribute,
        getgid=invalid_attribute,
    ):
        assert docker.get_docker_user() == ()


def test_docker_is_not_rootless():
    with mock.patch.object(
        docker, 'cmd_output',
        return_value=(0, DOCKER_NOT_ROOTLESS_SYSTEM_INFO, ''),
    ):
        assert docker._docker_is_rootless() is False


def test_docker_is_rootless():
    with mock.patch.object(
        docker, 'cmd_output',
        return_value=(0, DOCKER_ROOTLESS_SYSTEM_INFO, ''),
    ):
        assert docker._docker_is_rootless() is True


def test_podman_is_rootless():
    with mock.patch.object(
        docker, 'cmd_output',
        return_value=(0, PODMAN_SYSTEM_INFO, ''),
    ):
        assert docker._docker_is_rootless() is True
