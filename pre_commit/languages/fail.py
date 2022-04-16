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
    out = f'{hook.entry}\n\n'.encode()
    out += b'\n'.join(f.encode() for f in file_args) + b'\n'
    return 1, out
