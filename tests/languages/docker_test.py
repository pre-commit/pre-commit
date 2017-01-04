from __future__ import absolute_import
from __future__ import unicode_literals

import mock

from pre_commit.languages import docker
from pre_commit.util import CalledProcessError


def test_docker_is_running_process_error():
    with mock.patch(
        'pre_commit.languages.docker.cmd_output',
        side_effect=CalledProcessError(*(None,) * 4)
    ):
        assert docker.docker_is_running() is False
