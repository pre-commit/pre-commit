from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING

from pre_commit.languages import helpers
from pre_commit.languages.docker import assert_docker_available
from pre_commit.languages.docker import docker_cmd

if TYPE_CHECKING:
    from pre_commit.repository import Hook

ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(
        hook: 'Hook',
        file_args: Sequence[str],
        color: bool,
) -> Tuple[int, bytes]:  # pragma: windows no cover
    assert_docker_available()
    cmd = docker_cmd() + hook.cmd
    return helpers.run_xargs(hook, cmd, file_args, color=color)
