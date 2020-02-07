import contextlib
import os
import sys
from typing import Generator
from typing import Sequence
from typing import Tuple

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import PatchesT
from pre_commit.envcontext import Var
from pre_commit.hook import Hook
from pre_commit.languages import helpers
from pre_commit.languages.python import bin_dir
from pre_commit.prefix import Prefix
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.util import cmd_output_b

ENVIRONMENT_DIR = 'node_env'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def _envdir(prefix: Prefix, version: str) -> str:
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)
    return prefix.path(directory)


def get_env_patch(venv: str) -> PatchesT:
    if sys.platform == 'cygwin':  # pragma: no cover
        _, win_venv, _ = cmd_output('cygpath', '-w', venv)
        install_prefix = fr'{win_venv.strip()}\bin'
        lib_dir = 'lib'
    elif sys.platform == 'win32':  # pragma: no cover
        install_prefix = bin_dir(venv)
        lib_dir = 'Scripts'
    else:  # pragma: windows no cover
        install_prefix = venv
        lib_dir = 'lib'
    return (
        ('NODE_VIRTUAL_ENV', venv),
        ('NPM_CONFIG_PREFIX', install_prefix),
        ('npm_config_prefix', install_prefix),
        ('NODE_PATH', os.path.join(venv, lib_dir, 'node_modules')),
        ('PATH', (bin_dir(venv), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(
        prefix: Prefix,
        language_version: str,
) -> Generator[None, None, None]:
    with envcontext(get_env_patch(_envdir(prefix, language_version))):
        yield


def install_environment(
        prefix: Prefix, version: str, additional_dependencies: Sequence[str],
) -> None:
    additional_dependencies = tuple(additional_dependencies)
    assert prefix.exists('package.json')
    envdir = _envdir(prefix, version)

    # https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx?f=255&MSPPError=-2147217396#maxpath
    if sys.platform == 'win32':  # pragma: no cover
        envdir = f'\\\\?\\{os.path.normpath(envdir)}'
    with clean_path_on_failure(envdir):
        cmd = [
            sys.executable, '-mnodeenv', '--prebuilt', '--clean-src', envdir,
        ]
        if version != C.DEFAULT:
            cmd.extend(['-n', version])
        cmd_output_b(*cmd)

        with in_env(prefix, version):
            # https://npm.community/t/npm-install-g-git-vs-git-clone-cd-npm-install-g/5449
            # install as if we installed from git
            helpers.run_setup_cmd(prefix, ('npm', 'install'))
            helpers.run_setup_cmd(
                prefix,
                ('npm', 'install', '-g', '.', *additional_dependencies),
            )


def run_hook(
        hook: Hook,
        file_args: Sequence[str],
        color: bool,
) -> Tuple[int, bytes]:
    with in_env(hook.prefix, hook.language_version):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
