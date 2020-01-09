from unittest import mock

from pre_commit.languages import docker
from pre_commit.util import CalledProcessError


def test_docker_is_running_process_error():
    with mock.patch(
        'pre_commit.languages.docker.cmd_output_b',
        side_effect=CalledProcessError(None, None, None, None, None),
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
        assert docker.get_docker_user() == '1000:1000'
