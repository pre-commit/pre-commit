
import contextlib
from plumbum import local

from pre_commit.hooks_workspace import in_hooks_workspace


class Repository(object):
    def __init__(self, repo_config):
        self.repo_config = repo_config

    @property
    def repo_url(self):
        return self.repo_config['repo']

    @property
    def sha(self):
        return self.repo_config['sha']

    @contextlib.contextmanager
    def in_checkout(self):
        with in_hooks_workspace():
            with local.cwd(self.sha):
                yield

    def create(self):
        with in_hooks_workspace():
            if local.path(self.sha).exists():
                # Project already exists, no reason to re-create it
                return

            local['git']['clone', self.repo_url, self.sha]()
            with self.in_checkout():
                local['git']['checkout', self.sha]()

    def install(self):
        # Create if we have not already
        self.create()
        # TODO: need to take in the config here and determine if we actually
        # need to run any installers (and what languages to install)
        with self.in_checkout():
            if local.path('setup.py').exists():
                local['virtualenv']['py_env']()
                local['bash']['-c', 'source py_env/bin/activate && pip install .']()
