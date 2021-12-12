import contextlib
import os
import re
from typing import Generator
from typing import Sequence
from typing import Tuple

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.parse_shebang import find_executable
from pre_commit.prefix import Prefix
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output

ENVIRONMENT_DIR = 'lua_env'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def _find_lua(language_version: str) -> str:  # pragma: win32 no cover
    """Find a lua executable.

    Lua doesn't always have a plain `lua` executable.
    Some OS vendors will ship the binary as `lua#.#` (e.g., lua5.3)
    so discovery is needed to find a valid executable.
    """
    if language_version == C.DEFAULT:
        choices = ['lua']
        for path in os.environ.get('PATH', '').split(os.pathsep):
            try:
                candidates = os.listdir(path)
            except OSError:
                # Invalid path on PATH or lacking permissions.
                continue

            for candidate in candidates:
                # The Lua executable might look like `lua#.#` or `lua-#.#`.
                if re.search(r'^lua[-]?\d+\.\d+', candidate):
                    choices.append(candidate)
    else:
        # Prefer version specific executables first if available.
        # This should avoid the corner case where a user requests a language
        # version, gets a `lua` executable, but that executable is actually
        # for a different version and package.path would patch LUA_PATH
        # incorrectly.
        choices = [f'lua{language_version}', 'lua-{language_version}', 'lua']

    found_exes = [exe for exe in choices if find_executable(exe)]
    if found_exes:
        return found_exes[0]

    raise ValueError(
        'No lua executable found on the system paths '
        f'for {language_version} version.',
    )


def _get_lua_path_version(
        lua_executable: str,
) -> str:  # pragma: win32 no cover
    """Get the Lua version used in file paths."""
    # This could sniff out from _VERSION, but checking package.path should
    # provide an answer for *exactly* where lua is looking for packages.
    _, stdout, _ = cmd_output(lua_executable, '-e', 'print(package.path)')
    sep = os.sep if os.name != 'nt' else os.sep * 2
    match = re.search(fr'{sep}lua{sep}(.*?){sep}', stdout)
    if match:
        return match[1]

    raise ValueError('Cannot determine lua version for file paths.')


def get_env_patch(
        env: str, language_version: str,
) -> PatchesT:  # pragma: win32 no cover
    lua = _find_lua(language_version)
    version = _get_lua_path_version(lua)
    return (
        ('PATH', (os.path.join(env, 'bin'), os.pathsep, Var('PATH'))),
        (
            'LUA_PATH', (
                os.path.join(env, 'share', 'lua', version, '?.lua;'),
                os.path.join(env, 'share', 'lua', version, '?', 'init.lua;;'),
            ),
        ),
        (
            'LUA_CPATH', (
                os.path.join(env, 'lib', 'lua', version, '?.so;;'),
            ),
        ),
    )


def _envdir(prefix: Prefix, version: str) -> str:  # pragma: win32 no cover
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)
    return prefix.path(directory)


@contextlib.contextmanager  # pragma: win32 no cover
def in_env(
        prefix: Prefix,
        language_version: str,
) -> Generator[None, None, None]:
    with envcontext(
        get_env_patch(
            _envdir(prefix, language_version), language_version,
        ),
    ):
        yield


def install_environment(
    prefix: Prefix,
    version: str,
    additional_dependencies: Sequence[str],
) -> None:  # pragma: win32 no cover
    helpers.assert_version_default('lua', version)

    envdir = _envdir(prefix, version)
    with clean_path_on_failure(envdir):
        with in_env(prefix, version):
            # luarocks doesn't bootstrap a tree prior to installing
            # so ensure the directory exists.
            os.makedirs(envdir, exist_ok=True)

            make_cmd = ['luarocks', '--tree', envdir, 'make']
            # Older luarocks (e.g., 2.4.2) expect the rockspec as an argument.
            filenames = prefix.star('.rockspec')
            make_cmd.extend(filenames[:1])

            helpers.run_setup_cmd(prefix, tuple(make_cmd))

            # luarocks can't install multiple packages at once
            # so install them individually.
            for dependency in additional_dependencies:
                cmd = ('luarocks', '--tree', envdir, 'install', dependency)
                helpers.run_setup_cmd(prefix, cmd)


def run_hook(
    hook: Hook,
    file_args: Sequence[str],
    color: bool,
) -> Tuple[int, bytes]:  # pragma: win32 no cover
    with in_env(hook.prefix, hook.language_version):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
