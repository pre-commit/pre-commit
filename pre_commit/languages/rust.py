from __future__ import annotations

import contextlib
import functools
import os.path
import shutil
import sys
import tempfile
import urllib.request
from collections.abc import Generator
from collections.abc import Sequence

import pre_commit.constants as C
from pre_commit import lang_base
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.prefix import Prefix
from pre_commit.util import cmd_output_b
from pre_commit.util import make_executable
from pre_commit.util import win_exe

ENVIRONMENT_DIR = 'rustenv'
run_hook = lang_base.basic_run_hook


def health_check(prefix: Prefix, language_version: str) -> str | None:
    # For non-system versions, force a rebuild of:
    # - envs built by the previous layout (no `envdir/rustup/`), and
    # - envs whose installed toolchain no longer matches the configured
    #   `language_version` (e.g. user changed the version after install)
    # Without this, the rustup proxy at hook-run time would silently
    # auto-install the requested toolchain into the newly-pinned but
    # empty `envdir/rustup/`, using the user's globally-configured
    # `rustup set profile` (often `minimal` on CI -> no rustfmt).
    if language_version == 'system':
        return None
    envdir = lang_base.environment_dir(
        prefix, ENVIRONMENT_DIR, language_version,
    )
    for exe in ('rustup', 'cargo', 'rustc'):
        path = os.path.join(envdir, 'bin', win_exe(exe))
        if not os.path.isfile(path):
            return f'missing rust proxy at {path}'
    toolchains = os.path.join(envdir, 'rustup', 'toolchains')
    if not os.path.isdir(toolchains):
        return f'missing rust toolchain at {toolchains}'
    # rustup names toolchain dirs `<channel>-<host_triple>` (e.g.
    # `1.87.0-aarch64-apple-darwin`); a host-only build can just be
    # `<channel>`.  Either form should count as healthy.
    expected = _rust_toolchain(language_version)
    if not any(
            name == expected or name.startswith(f'{expected}-')
            for name in os.listdir(toolchains)
    ):
        return f'missing rust toolchain {expected} at {toolchains}'
    return None


@functools.lru_cache(maxsize=1)
def get_default_version() -> str:
    # If rust is already installed, we can save a bunch of setup time by
    # using the installed version.
    #
    # Just detecting the executable does not suffice, because if rustup is
    # installed but no toolchain is available, then `cargo` exists but
    # cannot be used without installing a toolchain first.
    if cmd_output_b('cargo', '--version', check=False, cwd='/')[0] == 0:
        return 'system'
    else:
        return C.DEFAULT


def _rust_toolchain(language_version: str) -> str:
    """Transform the language version into a rust toolchain version."""
    if language_version == C.DEFAULT:
        return 'stable'
    else:
        return language_version


def get_env_patch(target_dir: str, version: str) -> PatchesT:
    patches: PatchesT = (
        ('PATH', (os.path.join(target_dir, 'bin'), os.pathsep, Var('PATH'))),
    )
    # Pin `RUSTUP_HOME` inside `target_dir` so the installed toolchain
    # is found at both install- and hook-run time, instead of leaking to
    # `~/.rustup`.  `CARGO_HOME` is intentionally not overridden here so
    # cargo still picks up the user's `~/.cargo/{config,credentials}.toml`.
    if version != 'system':
        patches += (
            ('RUSTUP_HOME', os.path.join(target_dir, 'rustup')),
            ('RUSTUP_TOOLCHAIN', _rust_toolchain(version)),
        )
    return patches


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None]:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)
    with envcontext(get_env_patch(envdir, version)):
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

    lang_base.setup_cmd(prefix, ('cargo', 'add', *crates))


def install_rust_with_toolchain(toolchain: str, envdir: str) -> None:
    # `system` would degrade `get_env_patch` to PATH-only and let
    # rustup-init leak into `~/.rustup`; the caller already gates.
    if toolchain == 'system':
        raise ValueError(
            "install_rust_with_toolchain() does not support 'system'",
        )

    # Self-contained env setup: redundant when called from
    # `install_environment` (which entered `in_env` with the same patch),
    # but keeps this function safe to call directly.
    with envcontext(get_env_patch(envdir, toolchain)):
        # Check envdir directly rather than via `find_executable('rustup')`
        # so an existing system rustup doesn't suppress our bootstrap.
        if not os.path.isfile(
                os.path.join(envdir, 'bin', win_exe('rustup')),
        ):
            with tempfile.TemporaryDirectory() as init_dir:
                if sys.platform == 'win32':  # pragma: win32 cover
                    url = 'https://win.rustup.rs/x86_64'
                else:  # pragma: win32 no cover
                    url = 'https://sh.rustup.rs'

                rustup_init = os.path.join(init_dir, win_exe('rustup-init'))
                with urllib.request.urlopen(url) as resp, \
                        open(rustup_init, 'wb') as f:
                    shutil.copyfileobj(resp, f)
                make_executable(rustup_init)

                # `CARGO_HOME=envdir` only for rustup-init, so its proxy
                # binaries land in `envdir/bin/` instead of `~/.cargo/bin/`.
                with envcontext((('CARGO_HOME', envdir),)):
                    cmd_output_b(
                        rustup_init, '-y', '--quiet', '--no-modify-path',
                        '--default-toolchain', 'none',
                    )

        # Pin `--profile default` so rustfmt/clippy ship with the toolchain
        # even when the user's globally-configured `rustup set profile` is
        # `minimal` (common on CI images).
        cmd_output_b(
            'rustup', 'toolchain', 'install', '--no-self-update',
            '--profile', 'default', toolchain,
        )


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
    envdir = lang_base.environment_dir(prefix, ENVIRONMENT_DIR, version)

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

    packages_to_install: set[tuple[str, ...]] = {('--path', '.')}
    for cli_dep in cli_deps:
        cli_dep = cli_dep.removeprefix('cli:')
        package, _, crate_version = cli_dep.partition(':')
        if crate_version != '':
            packages_to_install.add((package, '--version', crate_version))
        else:
            packages_to_install.add((package,))

    with in_env(prefix, version):
        if version != 'system':
            install_rust_with_toolchain(_rust_toolchain(version), envdir)

        if len(lib_deps) > 0:
            _add_dependencies(prefix, lib_deps)

        for args in packages_to_install:
            cmd_output_b(
                'cargo', 'install', '--bins', '--root', envdir, *args,
                cwd=prefix.prefix_dir,
            )
