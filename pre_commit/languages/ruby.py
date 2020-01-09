import contextlib
import os.path
import shutil
import tarfile

import pre_commit.constants as C
from pre_commit.envcontext import envcontext
from pre_commit.envcontext import Var
from pre_commit.languages import helpers
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import resource_bytesio


ENVIRONMENT_DIR = 'rbenv'
get_default_version = helpers.basic_get_default_version
healthy = helpers.basic_healthy


def get_env_patch(venv, language_version):  # pragma: windows no cover
    patches = (
        ('GEM_HOME', os.path.join(venv, 'gems')),
        ('RBENV_ROOT', venv),
        ('BUNDLE_IGNORE_CONFIG', '1'),
        (
            'PATH', (
                os.path.join(venv, 'gems', 'bin'), os.pathsep,
                os.path.join(venv, 'shims'), os.pathsep,
                os.path.join(venv, 'bin'), os.pathsep, Var('PATH'),
            ),
        ),
    )
    if language_version != C.DEFAULT:
        patches += (('RBENV_VERSION', language_version),)
    return patches


@contextlib.contextmanager
def in_env(prefix, language_version):  # pragma: windows no cover
    envdir = prefix.path(
        helpers.environment_dir(ENVIRONMENT_DIR, language_version),
    )
    with envcontext(get_env_patch(envdir, language_version)):
        yield


def _extract_resource(filename, dest):
    with resource_bytesio(filename) as bio:
        with tarfile.open(fileobj=bio) as tf:
            tf.extractall(dest)


def _install_rbenv(prefix, version=C.DEFAULT):  # pragma: windows no cover
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    _extract_resource('rbenv.tar.gz', prefix.path('.'))
    shutil.move(prefix.path('rbenv'), prefix.path(directory))

    # Only install ruby-build if the version is specified
    if version != C.DEFAULT:
        plugins_dir = prefix.path(directory, 'plugins')
        _extract_resource('ruby-download.tar.gz', plugins_dir)
        _extract_resource('ruby-build.tar.gz', plugins_dir)

    activate_path = prefix.path(directory, 'bin', 'activate')
    with open(activate_path, 'w') as activate_file:
        # This is similar to how you would install rbenv to your home directory
        # However we do a couple things to make the executables exposed and
        # configure it to work in our directory.
        # We also modify the PS1 variable for manual debugging sake.
        activate_file.write(
            '#!/usr/bin/env bash\n'
            "export RBENV_ROOT='{directory}'\n"
            'export PATH="$RBENV_ROOT/bin:$PATH"\n'
            'eval "$(rbenv init -)"\n'
            'export PS1="(rbenv)$PS1"\n'
            # This lets us install gems in an isolated and repeatable
            # directory
            "export GEM_HOME='{directory}/gems'\n"
            'export PATH="$GEM_HOME/bin:$PATH"\n'
            '\n'.format(directory=prefix.path(directory)),
        )

        # If we aren't using the system ruby, add a version here
        if version != C.DEFAULT:
            activate_file.write(f'export RBENV_VERSION="{version}"\n')


def _install_ruby(prefix, version):  # pragma: windows no cover
    try:
        helpers.run_setup_cmd(prefix, ('rbenv', 'download', version))
    except CalledProcessError:  # pragma: no cover (usually find with download)
        # Failed to download from mirror for some reason, build it instead
        helpers.run_setup_cmd(prefix, ('rbenv', 'install', version))


def install_environment(
        prefix, version, additional_dependencies,
):  # pragma: windows no cover
    additional_dependencies = tuple(additional_dependencies)
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)
    with clean_path_on_failure(prefix.path(directory)):
        # TODO: this currently will fail if there's no version specified and
        # there's no system ruby installed.  Is this ok?
        _install_rbenv(prefix, version=version)
        with in_env(prefix, version):
            # Need to call this before installing so rbenv's directories are
            # set up
            helpers.run_setup_cmd(prefix, ('rbenv', 'init', '-'))
            if version != C.DEFAULT:
                _install_ruby(prefix, version)
            # Need to call this after installing to set up the shims
            helpers.run_setup_cmd(prefix, ('rbenv', 'rehash'))
            helpers.run_setup_cmd(
                prefix, ('gem', 'build') + prefix.star('.gemspec'),
            )
            helpers.run_setup_cmd(
                prefix,
                ('gem', 'install', '--no-document') +
                prefix.star('.gem') + additional_dependencies,
            )


def run_hook(hook, file_args, color):  # pragma: windows no cover
    with in_env(hook.prefix, hook.language_version):
        return helpers.run_xargs(hook, hook.cmd, file_args, color=color)
