from unittest import mock

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
