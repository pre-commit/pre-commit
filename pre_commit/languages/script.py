from __future__ import annotations

from typing import Sequence

from pre_commit.hook import Hook
from pre_commit.languages import helpers

ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check
install_environment = helpers.no_install


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> tuple[int, bytes]:
    cmd = (hook.prefix.path(hook.cmd[0]), *hook.cmd[1:])
    return helpers.run_xargs(hook, cmd, file_args, color=color)
