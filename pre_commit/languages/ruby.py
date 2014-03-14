
import contextlib
from plumbum import local

from pre_commit.languages import helpers


RVM_ENV = 'rvm_env'


class RubyEnv(object):
    def __init__(self):
        self.env_prefix = '. {0}/.rvm/scripts/rvm'.format(RVM_ENV)

    def run(self, cmd, **kwargs):
        return local['bash']['-c', ' '.join([self.env_prefix, cmd])].run(**kwargs)


@contextlib.contextmanager
def in_env():
    yield RubyEnv()


def install_environment():
    # Return immediately if we already have a virtualenv
    if local.path(RVM_ENV).exists():
        return

    local['__rvm-env.sh'][RVM_ENV]()
    with in_env() as env:
        env.run('bundle install')


def run_hook(hook, file_args):
    with in_env() as env:
        return helpers.run_hook(env, hook, file_args)