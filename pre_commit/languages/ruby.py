from __future__ import unicode_literals

import contextlib
import io
import shutil

from pre_commit.languages import helpers
from pre_commit.util import CalledProcessError
from pre_commit.util import clean_path_on_failure
from pre_commit.util import resource_filename
from pre_commit.util import tarfile_open


ENVIRONMENT_DIR = 'rbenv'


class RubyEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return '. {{prefix}}{0}/bin/activate &&'.format(
            helpers.environment_dir(ENVIRONMENT_DIR, self.language_version)
        )


@contextlib.contextmanager
def in_env(repo_cmd_runner, language_version):
    yield RubyEnv(repo_cmd_runner, language_version)


def _install_rbenv(repo_cmd_runner, version='default'):
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)

    with tarfile_open(resource_filename('rbenv.tar.gz')) as tf:
        tf.extractall(repo_cmd_runner.path('.'))
    shutil.move(
        repo_cmd_runner.path('rbenv'), repo_cmd_runner.path(directory),
    )

    # Only install ruby-build if the version is specified
    if version != 'default':
        # ruby-download
        with tarfile_open(resource_filename('ruby-download.tar.gz')) as tf:
            tf.extractall(repo_cmd_runner.path(directory, 'plugins'))

        # ruby-build
        with tarfile_open(resource_filename('ruby-build.tar.gz')) as tf:
            tf.extractall(repo_cmd_runner.path(directory, 'plugins'))

    activate_path = repo_cmd_runner.path(directory, 'bin', 'activate')
    with io.open(activate_path, 'w') as activate_file:
        # This is similar to how you would install rbenv to your home directory
        # However we do a couple things to make the executables exposed and
        # configure it to work in our directory.
        # We also modify the PS1 variable for manual debugging sake.
        activate_file.write(
            '#!/usr/bin/env bash\n'
            "export RBENV_ROOT='{0}'\n"
            'export PATH="$RBENV_ROOT/bin:$PATH"\n'
            'eval "$(rbenv init -)"\n'
            'export PS1="(rbenv)$PS1"\n'
            # This lets us install gems in an isolated and repeatable
            # directory
            "export GEM_HOME='{0}/gems'\n"
            'export PATH="$GEM_HOME/bin:$PATH"\n'
            '\n'.format(repo_cmd_runner.path(directory))
        )

        # If we aren't using the system ruby, add a version here
        if version != 'default':
            activate_file.write('export RBENV_VERSION="{0}"\n'.format(version))


def _install_ruby(environment, version):
    try:
        environment.run('rbenv download {0}'.format(version))
    except CalledProcessError:  # pragma: no cover (usually find with download)
        # Failed to download from mirror for some reason, build it instead
        environment.run('rbenv install {0}'.format(version))


def install_environment(repo_cmd_runner, version='default'):
    directory = helpers.environment_dir(ENVIRONMENT_DIR, version)
    with clean_path_on_failure(repo_cmd_runner.path(directory)):
        # TODO: this currently will fail if there's no version specified and
        # there's no system ruby installed.  Is this ok?
        _install_rbenv(repo_cmd_runner, version=version)
        with in_env(repo_cmd_runner, version) as ruby_env:
            if version != 'default':
                _install_ruby(ruby_env, version)
            ruby_env.run(
                'cd {prefix} && gem build *.gemspec'
                ' && gem install --no-document *.gem',
            )


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner, hook['language_version']) as env:
        return helpers.run_hook(env, hook, file_args)
