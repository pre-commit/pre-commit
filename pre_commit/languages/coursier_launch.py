from typing import Sequence
from typing import Tuple

from pre_commit.hook import Hook
from pre_commit.languages import helpers

ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy
install_environment = helpers.no_install


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> Tuple[int, bytes]:   # pragma: win32 no cover
    hook_cmd = hook.cmd
    forwarded_cmd = hook_cmd if '--' in hook_cmd else hook_cmd + ('--',)
    cmd = ('cs', 'launch') + forwarded_cmd
    return helpers.run_xargs(hook, cmd, file_args, color=color)
