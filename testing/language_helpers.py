from __future__ import annotations

import os
from typing import Sequence

import pre_commit.constants as C
from pre_commit.languages.all import Language
from pre_commit.prefix import Prefix


def run_language(
        path: os.PathLike[str],
        language: Language,
        exe: str,
        args: Sequence[str] = (),
        file_args: Sequence[str] = (),
        version: str = C.DEFAULT,
        deps: Sequence[str] = (),
        is_local: bool = False,
) -> tuple[int, bytes]:
    prefix = Prefix(str(path))

    language.install_environment(prefix, version, deps)
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
