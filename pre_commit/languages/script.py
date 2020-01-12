from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING

from pre_commit.languages import helpers

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
) -> Tuple[int, bytes]:
    cmd = hook.cmd
    cmd = (hook.prefix.path(cmd[0]),) + cmd[1:]
    return helpers.run_xargs(hook, cmd, file_args, color=color)
