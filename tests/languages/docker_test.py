from __future__ import absolute_import
from __future__ import unicode_literals

import mock

from pre_commit.languages import docker
from pre_commit.util import CalledProcessError


def test_docker_is_running_process_error():
    with mock.patch(
        'pre_commit.languages.docker.cmd_output',
        side_effect=CalledProcessError(*(None,) * 4),
    ):
        assert docker.docker_is_running() is False


def test_docker_fallback_uid():
    def invalid_attribute():
        raise AttributeError
    with mock.patch('os.getuid', invalid_attribute, create=True):
        assert docker.getuid() == docker.FALLBACK_UID


def test_docker_fallback_gid():
    def invalid_attribute():
        raise AttributeError
    with mock.patch('os.getgid', invalid_attribute, create=True):
        assert docker.getgid() == docker.FALLBACK_GID
