from __future__ import annotations

from typing import Protocol

from pre_commit.prefix import Prefix


class Tool(Protocol):
    # "special" versions which can be resolved
    @property
    def RESOLVABLE(self) -> tuple[str, ...]: ...
    # TODO: what if not resolvable? (no current examples?)
    def resolve(self, version: str) -> str: ...
    def install(self, prefix: Prefix, version: str) -> None: ...
    def health_check(self, prefix: Prefix, version: str) -> str | None: ...
    # TODO: how to env patch?
