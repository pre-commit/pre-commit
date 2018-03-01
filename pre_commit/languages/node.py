from __future__ import unicode_literals

import contextlib
import os
import sys

from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.languages.python import bin_dir
from pre_commit.util import clean_path_on_failure
from pre_commit.util import cmd_output
from pre_commit.xargs import xargs


ENVIRONMENT_DIR = 'node_env'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def _envdir(prefix, version):
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)
    return prefix.path(directory)


def get_env_patch(venv):
    if sys.platform == 'cygwin':  # pragma: no cover
        _, win_venv, _ = cmd_output('cygpath', '-w', venv)
        install_prefix = r'{}\bin'.format(win_venv.strip())
    elif sys.platform == 'win32':  # pragma: no cover
        install_prefix = bin_dir(venv)
    else:
        install_prefix = venv
    return (
        ('NODE_VIRTUAL_ENV', venv),
        ('NPM_CONFIG_PREFIX', install_prefix),
        ('npm_config_prefix', install_prefix),
        ('NODE_PATH', os.path.join(venv, 'lib', 'node_modules')),
        ('PATH', (bin_dir(venv), os.pathsep, Var('PATH'))),
    )


@contextlib.contextmanager
def in_env(prefix, language_version):
    with envcontext(get_env_patch(_envdir(prefix, language_version))):
        yield


def install_environment(prefix, version, additional_dependencies):
    additional_dependencies = tuple(additional_dependencies)
    assert prefix.exists('package.json')
    envdir = _envdir(prefix, version)

    # https://msdn.microsoft.com/en-us/library/windows/desktop/aa365247(v=vs.85).aspx?f=255&MSPPError=-2147217396#maxpath
    if sys.platform == 'win32':  # pragma: no cover
        envdir = '\\\\?\\' + os.path.normpath(envdir)
    with clean_path_on_failure(envdir):
        cmd = [
            sys.executable, '-mnodeenv', '--prebuilt', '--clean-src', envdir,
        ]
        if version != 'default':
            cmd.extend(['-n', version])
        cmd_output(*cmd)

        with in_env(prefix, version):
            helpers.run_setup_cmd(
                prefix,
                ('npm', 'install', '-g', '.') + additional_dependencies,
            )


def run_hook(prefix, hook, file_args):
    with in_env(prefix, hook['language_version']):
        return xargs(helpers.to_cmd(hook), file_args)
