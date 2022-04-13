from __future__ import annotations

from typing import Sequence

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
) -> tuple[int, bytes]:  # pragma: win32 no cover
    fullpath = (hook.prefix.prefix_dir + '\\' + hook.cmd[0])
    cmd = ('pwsh', '-F') + (fullpath,)
    return helpers.run_xargs(hook, cmd, file_args, color=color)
