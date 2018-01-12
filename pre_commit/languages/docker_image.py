from __future__ import absolute_import
from __future__ import unicode_literals

from pre_commit.languages import helpers
from pre_commit.languages.docker import assert_docker_available
from pre_commit.languages.docker import docker_cmd
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(prefix, hook, file_args):  # pragma: windows no cover
    assert_docker_available()
    cmd = docker_cmd() + helpers.to_cmd(hook)
    return xargs(cmd, file_args)
