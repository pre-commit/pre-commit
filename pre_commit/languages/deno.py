from __future__ import annotations

from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = None
get_default_version = lang_base.basic_get_default_version
install_environment = lang_base.no_install
in_env = lang_base.no_env


def health_check(prefix: Prefix, version: str) -> str | None:
    retcode, _, _ = cmd_output_b('deno', '--version', check=False)
    if retcode != 0:
        return f'`deno --version` returned {retcode}'
    else:
        return None


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
    cmd = ('deno', *lang_base.hook_cmd(entry, args))
    return lang_base.run_xargs(
        cmd,
        file_args,
        require_serial=require_serial,
        color=color,
    )
