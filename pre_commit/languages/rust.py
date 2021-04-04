import contextlib
import os.path
from typing import Generator
from typing import Sequence
from typing import Set
from typing import Tuple

import toml

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.prefix import Prefix
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'rustenv'
RUNTIME_DIR = 'rustup'
get_default_version = helpers.basic_get_default_version


def _envdir(prefix: Prefix, version: str) -> str:
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)
    return prefix.path(directory)


def _version_flag(version: str) -> Sequence[str]:
    return [] if version == C.DEFAULT else [f'+{version}']


def _resolve_version(prefix: Prefix, version: str) -> str:
    if version != C.DEFAULT:
        return version

    if prefix.exists('rust-toolchain'):
        with open(prefix.path('rust-toolchain')) as f:
            return f.readline().strip()

    return version


def get_env_patch(prefix: Prefix, version: str) -> PatchesT:
    env_path = _envdir(prefix, version)
    patch = (
        ('CARGO_HOME', env_path),
        ('PATH', (os.path.join(env_path, 'bin'), os.pathsep, Var('PATH'))),
    )

    if version != C.DEFAULT:
        return (*patch, ('RUSTUP_HOME', prefix.path(RUNTIME_DIR)))

    return patch


@contextlib.contextmanager
def in_env(prefix: Prefix, version: str) -> Generator[None, None, None]:
    with envcontext(get_env_patch(prefix, version)):
        yield


def healthy(prefix: Prefix, version: str) -> bool:
    language_version = _resolve_version(prefix, version)
    with in_env(prefix, language_version):
        version_flag = _version_flag(language_version)
        retcode, _, _ = cmd_output_b(
            'rustc', *version_flag, '--version',
            retcode=None,
            cwd=prefix.prefix_dir,
        )
        return retcode == 0


def _add_dependencies(
        cargo_toml_path: str,
        additional_dependencies: Set[str],
) -> None:
    with open(cargo_toml_path, 'r+') as f:
        cargo_toml = toml.load(f)
        cargo_toml.setdefault('dependencies', {})
        for dep in additional_dependencies:
            name, _, spec = dep.partition(':')
            cargo_toml['dependencies'][name] = spec or '*'
        f.seek(0)
        toml.dump(cargo_toml, f)
        f.truncate()


def install_environment(
        prefix: Prefix,
        version: str,
        additional_dependencies: Sequence[str],
) -> None:
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

    if len(lib_deps) > 0:
        _add_dependencies(prefix.path('Cargo.toml'), lib_deps)

    language_version = _resolve_version(prefix, version)
    directory = _envdir(prefix, language_version)
    with clean_path_on_failure(directory), in_env(prefix, language_version):
        if language_version != C.DEFAULT:
            cmd_output_b(
                'rustup', 'toolchain', 'install',
                '--no-self-update', '--profile', 'minimal', language_version,
                cwd=prefix.prefix_dir,
            )

        packages_to_install: Set[Tuple[str, ...]] = {('--path', '.')}
        for cli_dep in cli_deps:
            cli_dep = cli_dep[len('cli:'):]
            package, _, dep_version = cli_dep.partition(':')
            if dep_version != '':
                packages_to_install.add((package, '--version', dep_version))
            else:
                packages_to_install.add((package,))

        version_flag = _version_flag(language_version)
        for args in packages_to_install:
            cmd_output_b(
                'cargo', *version_flag, 'install', '--bins', *args,
                cwd=prefix.prefix_dir,
            )


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> Tuple[int, bytes]:
    language_version = _resolve_version(hook.prefix, hook.language_version)
    with in_env(hook.prefix, language_version):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
