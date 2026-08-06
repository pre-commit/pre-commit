from __future__ import annotations

from collections.abc import Sequence

from pre_commit import lang_base
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'deno_env'
get_default_version = lang_base.basic_get_default_version
in_env = lang_base.no_env
run_hook = lang_base.basic_run_hook


def health_check(prefix: Prefix, version: str) -> str | None:
    retcode, _, _ = cmd_output_b('deno', '--version', check=False)
    if retcode != 0:
        return f'`deno --version` returned {retcode}'
    else:
        return None


def install_environment(
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:
    lang_base.assert_version_default('deno', version)
    lang_base.assert_no_additional_deps('deno', additional_dependencies)
