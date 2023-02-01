from __future__ import annotations

import os
from typing import Sequence

from pre_commit.languages.all import Language
from pre_commit.prefix import Prefix


def run_language(
        path: os.PathLike[str],
        language: Language,
        exe: str,
        args: Sequence[str] = (),
        file_args: Sequence[str] = (),
        version: str | None = None,
        deps: Sequence[str] = (),
        is_local: bool = False,
) -> tuple[int, bytes]:
    prefix = Prefix(str(path))
    version = version or language.get_default_version()

    language.install_environment(prefix, version, deps)
    health_error = language.health_check(prefix, version)
    assert health_error is None, health_error
    with language.in_env(prefix, version):
        ret, out = language.run_hook(
            prefix,
            exe,
            args,
            file_args,
            is_local=is_local,
            require_serial=True,
            color=False,
        )
        out = out.replace(b'\r\n', b'\n')
        return ret, out
