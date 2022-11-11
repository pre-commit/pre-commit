from __future__ import annotations

import contextlib
import functools
import os.path
import shutil
import sys
import tempfile
import urllib.request
from typing import Generator
from typing import Sequence

import pre_commit.constants as C
from pre_commit import parse_shebang
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output_b
from pre_commit.util import make_executable
from pre_commit.util import win_exe

ENVIRONMENT_DIR = 'rustenv'
health_check = helpers.basic_health_check


@functools.lru_cache(maxsize=1)
def get_default_version() -> str:
    # If rust is already installed, we can save a bunch of setup time by
    # using the installed version.
    #
    # Just detecting the executable does not suffice, because if rustup is
    # installed but no toolchain is available, then `cargo` exists but
    # cannot be used without installing a toolchain first.
    if cmd_output_b('cargo', '--version', check=False)[0] == 0:
        return 'system'
    else:
        return C.DEFAULT


def _rust_toolchain(language_version: str) -> str:
    """Transform the language version into a rust toolchain version."""
    if language_version == C.DEFAULT:
        return 'stable'
    else:
        return language_version


def _envdir(prefix: Prefix, version: str) -> str:
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)
    return prefix.path(directory)


def get_env_patch(target_dir: str, version: str) -> PatchesT:
    return (
        ('CARGO_HOME', target_dir),
        ('PATH', (os.path.join(target_dir, 'bin'), os.pathsep, Var('PATH'))),
        # Only set RUSTUP_TOOLCHAIN if we don't want use the system's default
        # toolchain
        *(
            (('RUSTUP_TOOLCHAIN', _rust_toolchain(version)),)
            if version != 'system' else ()
        ),
    )


@contextlib.contextmanager
def in_env(
    prefix: Prefix,
    language_version: str,
) -> Generator[None, None, None]:
    with envcontext(
        get_env_patch(_envdir(prefix, language_version), language_version),
    ):
        yield


def _add_dependencies(
        prefix: Prefix,
        additional_dependencies: set[str],
) -> None:
    crates = []
    for dep in additional_dependencies:
        name, _, spec = dep.partition(':')
        crate = f'{name}@{spec or "*"}'
        crates.append(crate)

    helpers.run_setup_cmd(prefix, ('cargo', 'add', *crates))


def install_rust_with_toolchain(toolchain: str) -> None:
    with tempfile.TemporaryDirectory() as rustup_dir:
        with envcontext((('RUSTUP_HOME', rustup_dir),)):
            # acquire `rustup` if not present
            if parse_shebang.find_executable('rustup') is None:
                # We did not detect rustup and need to download it first.
                if sys.platform == 'win32':  # pragma: win32 cover
                    url = 'https://win.rustup.rs/x86_64'
                else:  # pragma: win32 no cover
                    url = 'https://sh.rustup.rs'

                resp = urllib.request.urlopen(url)

                rustup_init = os.path.join(rustup_dir, win_exe('rustup-init'))
                with open(rustup_init, 'wb') as f:
                    shutil.copyfileobj(resp, f)
                make_executable(rustup_init)

                # install rustup into `$CARGO_HOME/bin`
                cmd_output_b(
                    rustup_init, '-y', '--quiet', '--no-modify-path',
                    '--default-toolchain', 'none',
                )

            cmd_output_b(
                'rustup', 'toolchain', 'install', '--no-self-update',
                toolchain,
            )


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    directory = _envdir(prefix, version)

    # There are two cases where we might want to specify more dependencies:
    # as dependencies for the library being built, and as binary packages
    # to be `cargo install`'d.
    #
    # Unlike e.g. Python, if we just `cargo install` a library, it won't be
    # used for compilation. And if we add a crate providing a binary to the
    # `Cargo.toml`, the binary won't be built.
    #
    # Because of this, we allow specifying "cli" dependencies by prefixing
    # with 'cli:'.
    cli_deps = {
        dep for dep in additional_dependencies if dep.startswith('cli:')
    }
    lib_deps = set(additional_dependencies) - cli_deps

    with clean_path_on_failure(directory):
        packages_to_install: set[tuple[str, ...]] = {('--path', '.')}
        for cli_dep in cli_deps:
            cli_dep = cli_dep[len('cli:'):]
            package, _, crate_version = cli_dep.partition(':')
            if crate_version != '':
                packages_to_install.add((package, '--version', crate_version))
            else:
                packages_to_install.add((package,))

        with in_env(prefix, version):
            if version != 'system':
                install_rust_with_toolchain(_rust_toolchain(version))

            if len(lib_deps) > 0:
                _add_dependencies(prefix, lib_deps)

            for args in packages_to_install:
                cmd_output_b(
                    'cargo', 'install', '--bins', '--root', directory, *args,
                    cwd=prefix.prefix_dir,
                )


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> tuple[int, bytes]:
    with in_env(hook.prefix, hook.language_version):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
