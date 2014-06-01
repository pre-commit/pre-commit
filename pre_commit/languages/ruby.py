from __future__ import unicode_literals

import contextlib
import io
import os

from pre_commit.languages import helpers
from pre_commit.util import clean_path_on_failure


ENVIRONMENT_DIR = 'rbenv'


class RubyEnv(helpers.Environment):
    @property
    def env_prefix(self):
        return '. {{prefix}}{0}/bin/activate &&'.format(ENVIRONMENT_DIR)

    def run(self, *args, **kwargs):
        # TODO: hardcoded version smell
        env = dict(os.environ, RBENV_VERSION='1.9.3-p547')
        return super(RubyEnv, self).run(*args, env=env, **kwargs)


@contextlib.contextmanager
def in_env(repo_cmd_runner):
    yield RubyEnv(repo_cmd_runner)


def _install_rbenv(repo_cmd_runner):
    repo_cmd_runner.run([
        'git', 'clone', 'git://github.com/sstephenson/rbenv', '{prefix}rbenv',
    ])
    repo_cmd_runner.run([
        'git', 'clone', 'git://github.com/sstephenson/ruby-build',
        '{prefix}rbenv/plugins/ruby-build',
    ])

    activate_path = repo_cmd_runner.path('rbenv', 'bin', 'activate')
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
            '\n'.format(repo_cmd_runner.path('rbenv'))
        )


def install_environment(repo_cmd_runner):
    with clean_path_on_failure(repo_cmd_runner.path('rbenv')):
        _install_rbenv(repo_cmd_runner)
        with in_env(repo_cmd_runner) as ruby_env:
            # TODO: hardcoded version smell
            ruby_env.run('rbenv install 1.9.3-p547')
            ruby_env.run(
                'cd {prefix} && gem build *.gemspec && gem install *.gem',
            )


def run_hook(repo_cmd_runner, hook, file_args):
    with in_env(repo_cmd_runner) as env:
        return helpers.run_hook(env, hook, file_args)
