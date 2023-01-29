from __future__ import annotations

from typing import ContextManager
from typing import Protocol
from typing import Sequence

from pre_commit.languages import conda
from pre_commit.languages import coursier
from pre_commit.languages import dart
from pre_commit.languages import docker
from pre_commit.languages import docker_image
from pre_commit.languages import dotnet
from pre_commit.languages import fail
from pre_commit.languages import golang
from pre_commit.languages import lua
from pre_commit.languages import node
from pre_commit.languages import perl
from pre_commit.languages import pygrep
from pre_commit.languages import python
from pre_commit.languages import r
from pre_commit.languages import ruby
from pre_commit.languages import rust
from pre_commit.languages import script
from pre_commit.languages import swift
from pre_commit.languages import system
from pre_commit.prefix import Prefix


class Language(Protocol):
    # Use `None` for no installation / environment
    @property
    def ENVIRONMENT_DIR(self) -> str | None: ...
    # return a value to replace `'default` for `language_version`
    def get_default_version(self) -> str: ...

    # return whether the environment is healthy (or should be rebuilt)
    def health_check(
            self,
            prefix: Prefix,
            language_version: str,
    ) -> str | None:
        ...

    # install a repository for the given language and language_version
    def install_environment(
            self,
            prefix: Prefix,
            version: str,
            additional_dependencies: Sequence[str],
    ) -> None:
        ...

    # modify the environment for hook execution
    def in_env(
            self,
            prefix: Prefix,
            version: str,
    ) -> ContextManager[None]:
        ...

    # execute a hook and return the exit code and output
    def run_hook(
            self,
            prefix: Prefix,
            entry: str,
            args: Sequence[str],
            file_args: Sequence[str],
            *,
            is_local: bool,
            require_serial: bool,
            color: bool,
    ) -> tuple[int, bytes]:
        ...


languages: dict[str, Language] = {
    'conda': conda,
    'coursier': coursier,
    'dart': dart,
    'docker': docker,
    'docker_image': docker_image,
    'dotnet': dotnet,
    'fail': fail,
    'golang': golang,
    'lua': lua,
    'node': node,
    'perl': perl,
    'pygrep': pygrep,
    'python': python,
    'r': r,
    'ruby': ruby,
    'rust': rust,
    'script': script,
    'swift': swift,
    'system': system,
    # TODO: fully deprecate `python_venv`
    'python_venv': python,
}
all_languages = sorted(languages)
