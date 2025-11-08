from __future__ import annotations

from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.languages.docker import docker_cmd
from pre_commit.prefix import Prefix

ENVIRONMENT_DIR = None
get_default_version = lang_base.basic_get_default_version
health_check = lang_base.basic_health_check
install_environment = lang_base.no_install
in_env = lang_base.no_env


def run_hook(
        prefix: Prefix,
        entry: str,
        args: Sequence[str],
        file_args: Sequence[str],
        *,
        is_local: bool,
        require_serial: bool,
        color: bool,
) -> tuple[int, bytes]:  # pragma: win32 no cover
    cmd = lang_base.hook_cmd(entry, args)

    # To prevent duplicate simultaneous image pull attempts in `run_xargs`, we
    # try to precache the Docker image by pulling it here first
    try:
        image_name = cmd[2 if cmd[0] == '--entrypoint' else 0]
        lang_base.setup_cmd(prefix, ('docker', 'pull', image_name))
    except Exception:
        pass

    return lang_base.run_xargs(
        docker_cmd(color=color) + cmd,
        file_args,
        require_serial=require_serial,
        color=color,
    )
