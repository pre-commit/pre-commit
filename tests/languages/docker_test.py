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

DOCKER_CGROUPS_V1_MOUNTINFO_EXAMPLE = b'''\
759 717 0:52 / / rw,relatime master:300 - overlay overlay rw,lowerdir=/var/lib/docker/overlay2/l/PCPE5P5IVGM7CFCPJR353N3ONK:/var/lib/docker/overlay2/l/EQFSDHFAJ333VEMEJD4ZTRIZCB,upperdir=/var/lib/docker/overlay2/0d9f6bf186030d796505b87d6daa92297355e47641e283d3c09d83a7f221e462/diff,workdir=/var/lib/docker/overlay2/0d9f6bf186030d796505b87d6daa92297355e47641e283d3c09d83a7f221e462/work
760 759 0:58 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
761 759 0:59 / /dev rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
762 761 0:60 / /dev/pts rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
763 759 0:61 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs ro
764 763 0:62 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime - tmpfs tmpfs rw,mode=755,inode64
765 764 0:29 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/systemd ro,nosuid,nodev,noexec,relatime master:11 - cgroup cgroup rw,xattr,name=systemd
766 764 0:32 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/rdma ro,nosuid,nodev,noexec,relatime master:15 - cgroup cgroup rw,rdma
767 764 0:33 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/cpu,cpuacct ro,nosuid,nodev,noexec,relatime master:16 - cgroup cgroup rw,cpu,cpuacct
768 764 0:34 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/cpuset ro,nosuid,nodev,noexec,relatime master:17 - cgroup cgroup rw,cpuset
769 764 0:35 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/pids ro,nosuid,nodev,noexec,relatime master:18 - cgroup cgroup rw,pids
770 764 0:36 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/memory ro,nosuid,nodev,noexec,relatime master:19 - cgroup cgroup rw,memory
771 764 0:37 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/perf_event ro,nosuid,nodev,noexec,relatime master:20 - cgroup cgroup rw,perf_event
772 764 0:38 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/net_cls,net_prio ro,nosuid,nodev,noexec,relatime master:21 - cgroup cgroup rw,net_cls,net_prio
773 764 0:39 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/blkio ro,nosuid,nodev,noexec,relatime master:22 - cgroup cgroup rw,blkio
774 764 0:40 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/misc ro,nosuid,nodev,noexec,relatime master:23 - cgroup cgroup rw,misc
775 764 0:41 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/hugetlb ro,nosuid,nodev,noexec,relatime master:24 - cgroup cgroup rw,hugetlb
776 764 0:42 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/devices ro,nosuid,nodev,noexec,relatime master:25 - cgroup cgroup rw,devices
777 764 0:43 /docker/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7 /sys/fs/cgroup/freezer ro,nosuid,nodev,noexec,relatime master:26 - cgroup cgroup rw,freezer
778 761 0:57 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
779 761 0:63 / /dev/shm rw,nosuid,nodev,noexec,relatime - tmpfs shm rw,size=65536k,inode64
780 759 8:5 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/resolv.conf /etc/resolv.conf rw,relatime - ext4 /dev/sda5 rw,errors=remount-ro
781 759 8:5 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/hostname /etc/hostname rw,relatime - ext4 /dev/sda5 rw,errors=remount-ro
782 759 8:5 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/hosts /etc/hosts rw,relatime - ext4 /dev/sda5 rw,errors=remount-ro
718 761 0:60 /0 /dev/console rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
719 760 0:58 /bus /proc/bus ro,nosuid,nodev,noexec,relatime - proc proc rw
720 760 0:58 /fs /proc/fs ro,nosuid,nodev,noexec,relatime - proc proc rw
721 760 0:58 /irq /proc/irq ro,nosuid,nodev,noexec,relatime - proc proc rw
722 760 0:58 /sys /proc/sys ro,nosuid,nodev,noexec,relatime - proc proc rw
723 760 0:58 /sysrq-trigger /proc/sysrq-trigger ro,nosuid,nodev,noexec,relatime - proc proc rw
724 760 0:64 / /proc/asound ro,relatime - tmpfs tmpfs ro,inode64
725 760 0:65 / /proc/acpi ro,relatime - tmpfs tmpfs ro,inode64
726 760 0:59 /null /proc/kcore rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
727 760 0:59 /null /proc/keys rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
728 760 0:59 /null /proc/timer_list rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
729 760 0:66 / /proc/scsi ro,relatime - tmpfs tmpfs ro,inode64
730 763 0:67 / /sys/firmware ro,relatime - tmpfs tmpfs ro,inode64
731 763 0:68 / /sys/devices/virtual/powercap ro,relatime - tmpfs tmpfs ro,inode64
'''  # noqa: E501

DOCKER_CGROUPS_V2_MOUNTINFO_EXAMPLE = b'''\
721 386 0:45 / / rw,relatime master:218 - overlay overlay rw,lowerdir=/var/lib/docker/overlay2/l/QHZ7OM7P4AQD3XLG274ZPWAJCV:/var/lib/docker/overlay2/l/5RFG6SZWVGOG2NKEYXJDQCQYX5,upperdir=/var/lib/docker/overlay2/e4ad859fc5d4791932b9b976052f01fb0063e01de3cef916e40ae2121f6a166e/diff,workdir=/var/lib/docker/overlay2/e4ad859fc5d4791932b9b976052f01fb0063e01de3cef916e40ae2121f6a166e/work,nouserxattr
722 721 0:48 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
723 721 0:50 / /dev rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
724 723 0:51 / /dev/pts rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
725 721 0:52 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs ro
726 725 0:26 / /sys/fs/cgroup ro,nosuid,nodev,noexec,relatime - cgroup2 cgroup rw,nsdelegate,memory_recursiveprot
727 723 0:47 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
728 723 0:53 / /dev/shm rw,nosuid,nodev,noexec,relatime - tmpfs shm rw,size=65536k,inode64
729 721 8:3 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/resolv.conf /etc/resolv.conf rw,relatime - ext4 /dev/sda3 rw,errors=remount-ro
730 721 8:3 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/hostname /etc/hostname rw,relatime - ext4 /dev/sda3 rw,errors=remount-ro
731 721 8:3 /var/lib/docker/containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/hosts /etc/hosts rw,relatime - ext4 /dev/sda3 rw,errors=remount-ro
387 723 0:51 /0 /dev/console rw,nosuid,noexec,relatime - devpts devpts rw,gid=5,mode=620,ptmxmode=666
388 722 0:48 /bus /proc/bus ro,nosuid,nodev,noexec,relatime - proc proc rw
389 722 0:48 /fs /proc/fs ro,nosuid,nodev,noexec,relatime - proc proc rw
525 722 0:48 /irq /proc/irq ro,nosuid,nodev,noexec,relatime - proc proc rw
526 722 0:48 /sys /proc/sys ro,nosuid,nodev,noexec,relatime - proc proc rw
571 722 0:48 /sysrq-trigger /proc/sysrq-trigger ro,nosuid,nodev,noexec,relatime - proc proc rw
572 722 0:57 / /proc/asound ro,relatime - tmpfs tmpfs ro,inode64
575 722 0:58 / /proc/acpi ro,relatime - tmpfs tmpfs ro,inode64
576 722 0:50 /null /proc/kcore rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
577 722 0:50 /null /proc/keys rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
578 722 0:50 /null /proc/timer_list rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,inode64
579 722 0:59 / /proc/scsi ro,relatime - tmpfs tmpfs ro,inode64
580 725 0:60 / /sys/firmware ro,relatime - tmpfs tmpfs ro,inode64
'''  # noqa: E501

PODMAN_CGROUPS_V1_MOUNTINFO_EXAMPLE = b'''\
1200 915 0:57 / / rw,relatime - overlay overlay rw,lowerdir=/home/asottile/.local/share/containers/storage/overlay/l/ZWAU3VY3ZHABQJRBUAFPBX7R5D,upperdir=/home/asottile/.local/share/containers/storage/overlay/72504ef163fda63838930450553b7306412ccad139a007626732b3dc43af5200/diff,workdir=/home/asottile/.local/share/containers/storage/overlay/72504ef163fda63838930450553b7306412ccad139a007626732b3dc43af5200/work,volatile,userxattr
1204 1200 0:62 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
1205 1200 0:63 / /dev rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,uid=1000,gid=1000,inode64
1206 1200 0:64 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs rw
1207 1205 0:65 / /dev/pts rw,nosuid,noexec,relatime - devpts devpts rw,gid=100004,mode=620,ptmxmode=666
1208 1205 0:61 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
1209 1200 0:53 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/.containerenv /run/.containerenv rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=814036k,mode=700,uid=1000,gid=1000,inode64
1210 1200 0:53 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/resolv.conf /etc/resolv.conf rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=814036k,mode=700,uid=1000,gid=1000,inode64
1211 1200 0:53 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/hosts /etc/hosts rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=814036k,mode=700,uid=1000,gid=1000,inode64
1212 1205 0:56 / /dev/shm rw,relatime - tmpfs shm rw,size=64000k,uid=1000,gid=1000,inode64
1213 1200 0:53 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/hostname /etc/hostname rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=814036k,mode=700,uid=1000,gid=1000,inode64
1214 1206 0:66 / /sys/fs/cgroup rw,nosuid,nodev,noexec,relatime - tmpfs cgroup rw,size=1024k,uid=1000,gid=1000,inode64
1215 1214 0:43 / /sys/fs/cgroup/freezer ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,freezer
1216 1214 0:42 /user.slice /sys/fs/cgroup/devices ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,devices
1217 1214 0:41 / /sys/fs/cgroup/hugetlb ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,hugetlb
1218 1214 0:40 / /sys/fs/cgroup/misc ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,misc
1219 1214 0:39 / /sys/fs/cgroup/blkio ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,blkio
1220 1214 0:38 / /sys/fs/cgroup/net_cls,net_prio ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,net_cls,net_prio
1221 1214 0:37 / /sys/fs/cgroup/perf_event ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,perf_event
1222 1214 0:36 /user.slice/user-1000.slice/user@1000.service /sys/fs/cgroup/memory ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,memory
1223 1214 0:35 /user.slice/user-1000.slice/user@1000.service /sys/fs/cgroup/pids ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,pids
1224 1214 0:34 / /sys/fs/cgroup/cpuset ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,cpuset
1225 1214 0:33 / /sys/fs/cgroup/cpu,cpuacct ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,cpu,cpuacct
1226 1214 0:32 / /sys/fs/cgroup/rdma ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,rdma
1227 1214 0:29 /user.slice/user-1000.slice/user@1000.service/apps.slice/apps-org.gnome.Terminal.slice/vte-spawn-0c50448e-b395-4d76-8b92-379f16e5066f.scope /sys/fs/cgroup/systemd ro,nosuid,nodev,noexec,relatime - cgroup cgroup rw,xattr,name=systemd
1228 1205 0:5 /null /dev/null rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1229 1205 0:5 /zero /dev/zero rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1230 1205 0:5 /full /dev/full rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1231 1205 0:5 /tty /dev/tty rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1232 1205 0:5 /random /dev/random rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1233 1205 0:5 /urandom /dev/urandom rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1234 1204 0:67 / /proc/acpi ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
1235 1204 0:5 /null /proc/kcore rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1236 1204 0:5 /null /proc/keys rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1237 1204 0:5 /null /proc/timer_list rw,nosuid,noexec,relatime - devtmpfs udev rw,size=4031656k,nr_inodes=1007914,mode=755,inode64
1238 1204 0:68 / /proc/scsi ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
1239 1206 0:69 / /sys/firmware ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
1240 1206 0:70 / /sys/dev/block ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
1241 1204 0:62 /asound /proc/asound ro,relatime - proc proc rw
1242 1204 0:62 /bus /proc/bus ro,relatime - proc proc rw
1243 1204 0:62 /fs /proc/fs ro,relatime - proc proc rw
1244 1204 0:62 /irq /proc/irq ro,relatime - proc proc rw
1245 1204 0:62 /sys /proc/sys ro,relatime - proc proc rw
1256 1204 0:62 /sysrq-trigger /proc/sysrq-trigger ro,relatime - proc proc rw
916 1205 0:65 /0 /dev/console rw,relatime - devpts devpts rw,gid=100004,mode=620,ptmxmode=666
'''  # noqa: E501

PODMAN_CGROUPS_V2_MOUNTINFO_EXAMPLE = b'''\
685 690 0:63 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/resolv.conf /etc/resolv.conf rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=1637624k,nr_inodes=409406,mode=700,uid=1000,gid=1000,inode64
686 690 0:63 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/hosts /etc/hosts rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=1637624k,nr_inodes=409406,mode=700,uid=1000,gid=1000,inode64
687 692 0:50 / /dev/shm rw,nosuid,nodev,noexec,relatime - tmpfs shm rw,size=64000k,uid=1000,gid=1000,inode64
688 690 0:63 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/.containerenv /run/.containerenv rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=1637624k,nr_inodes=409406,mode=700,uid=1000,gid=1000,inode64
689 690 0:63 /containers/overlay-containers/c33988ec7651ebc867cb24755eaf637a6734088bc7eef59d5799293a9e5450f7/userdata/hostname /etc/hostname rw,nosuid,nodev,relatime - tmpfs tmpfs rw,size=1637624k,nr_inodes=409406,mode=700,uid=1000,gid=1000,inode64
690 546 0:55 / / rw,relatime - overlay overlay rw,lowerdir=/home/asottile/.local/share/containers/storage/overlay/l/NPOHYOD3PI3YW6TQSGBOVOUSK6,upperdir=/home/asottile/.local/share/containers/storage/overlay/565c206fb79f876ffd5f069b8bd7a97fb5e47d5d07396b0c395a4ed6725d4a8e/diff,workdir=/home/asottile/.local/share/containers/storage/overlay/565c206fb79f876ffd5f069b8bd7a97fb5e47d5d07396b0c395a4ed6725d4a8e/work,redirect_dir=nofollow,uuid=on,volatile,userxattr
691 690 0:59 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw
692 690 0:61 / /dev rw,nosuid - tmpfs tmpfs rw,size=65536k,mode=755,uid=1000,gid=1000,inode64
693 690 0:62 / /sys ro,nosuid,nodev,noexec,relatime - sysfs sysfs rw
694 692 0:66 / /dev/pts rw,nosuid,noexec,relatime - devpts devpts rw,gid=100004,mode=620,ptmxmode=666
695 692 0:58 / /dev/mqueue rw,nosuid,nodev,noexec,relatime - mqueue mqueue rw
696 693 0:28 / /sys/fs/cgroup ro,nosuid,nodev,noexec,relatime - cgroup2 cgroup2 rw,nsdelegate,memory_recursiveprot
698 692 0:6 /null /dev/null rw,nosuid,noexec,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
699 692 0:6 /zero /dev/zero rw,nosuid,noexec,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
700 692 0:6 /full /dev/full rw,nosuid,noexec,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
701 692 0:6 /tty /dev/tty rw,nosuid,noexec,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
702 692 0:6 /random /dev/random rw,nosuid,noexec,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
703 692 0:6 /urandom /dev/urandom rw,nosuid,noexec,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
704 691 0:67 / /proc/acpi ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
705 691 0:6 /null /proc/kcore ro,nosuid,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
706 691 0:6 /null /proc/keys ro,nosuid,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
707 691 0:6 /null /proc/latency_stats ro,nosuid,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
708 691 0:6 /null /proc/timer_list ro,nosuid,relatime - devtmpfs udev rw,size=8147812k,nr_inodes=2036953,mode=755,inode64
709 691 0:68 / /proc/scsi ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
710 693 0:69 / /sys/firmware ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
711 693 0:70 / /sys/dev/block ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
712 693 0:71 / /sys/devices/virtual/powercap ro,relatime - tmpfs tmpfs rw,size=0k,uid=1000,gid=1000,inode64
713 691 0:59 /asound /proc/asound ro,nosuid,nodev,noexec,relatime - proc proc rw
714 691 0:59 /bus /proc/bus ro,nosuid,nodev,noexec,relatime - proc proc rw
715 691 0:59 /fs /proc/fs ro,nosuid,nodev,noexec,relatime - proc proc rw
716 691 0:59 /irq /proc/irq ro,nosuid,nodev,noexec,relatime - proc proc rw
717 691 0:59 /sys /proc/sys ro,nosuid,nodev,noexec,relatime - proc proc rw
718 691 0:59 /sysrq-trigger /proc/sysrq-trigger ro,nosuid,nodev,noexec,relatime - proc proc rw
547 692 0:66 /0 /dev/console rw,relatime - devpts devpts rw,gid=100004,mode=620,ptmxmode=666
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
        (0, b'{"response_from_some_other_container_engine": true}', b''),
        (0, b'{"SecurityOptions": null}', b''),
        (1, b'', b''),
    ),
)
def test_docker_user_non_rootless(info_ret):
    with mock.patch.object(docker, 'cmd_output_b', return_value=info_ret):
        assert docker.get_docker_user() != ()


def test_container_id_no_file():
    with mock.patch.object(builtins, 'open', side_effect=FileNotFoundError):
        assert docker._get_container_id() is None


def _mock_open(data):
    return mock.patch.object(
        builtins,
        'open',
        new_callable=mock.mock_open,
        read_data=data,
    )


def test_container_id_not_in_file():
    with _mock_open(NON_DOCKER_MOUNTINFO_EXAMPLE):
        assert docker._get_container_id() is None


def test_get_container_id():
    with _mock_open(DOCKER_CGROUPS_V1_MOUNTINFO_EXAMPLE):
        assert docker._get_container_id() == CONTAINER_ID
    with _mock_open(DOCKER_CGROUPS_V2_MOUNTINFO_EXAMPLE):
        assert docker._get_container_id() == CONTAINER_ID
    with _mock_open(PODMAN_CGROUPS_V1_MOUNTINFO_EXAMPLE):
        assert docker._get_container_id() == CONTAINER_ID
    with _mock_open(PODMAN_CGROUPS_V2_MOUNTINFO_EXAMPLE):
        assert docker._get_container_id() == CONTAINER_ID


def test_get_docker_path_not_in_docker_returns_same():
    with _mock_open(b''):
        assert docker._get_docker_path('abc') == 'abc'


@pytest.fixture
def in_docker():
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
