from __future__ import annotations

from typing import Sequence

from pre_commit.languages import helpers
from pre_commit.prefix import Prefix

ENVIRONMENT_DIR = None
get_default_version = helpers.basic_get_default_version
health_check = helpers.basic_health_check
install_environment = helpers.no_install
in_env = helpers.no_env


def run_hook(
        prefix: Prefix,
        entry: str,
        args: Sequence[str],
        file_args: Sequence[str],
        *,
        is_local: bool,
        require_serial: bool,
        color: bool,
) -> tuple[int, bytes]:
    cmd = helpers.hook_cmd(entry, args)
    cmd = (prefix.path(cmd[0]), *cmd[1:])
    return helpers.run_xargs(
        cmd,
        file_args,
        require_serial=require_serial,
        color=color,
    )
