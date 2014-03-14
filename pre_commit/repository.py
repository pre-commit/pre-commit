
import contextlib
from plumbum import local

import pre_commit.constants as C
from pre_commit.clientlib.validate_manifest import validate_manifest
from pre_commit.hooks_workspace import in_hooks_workspace
from pre_commit.util import cached_property


def install_python(repo):
    assert local.path('setup.py').exists()
    local['virtualenv']['py_env']()
    local['bash']['-c', 'source py_env/bin/activate && pip install .']()


def install_ruby(repo):
    raise NotImplementedError


def install_node(repo):
    raise NotImplementedError


language_to_repo_setup_strategy = {
    'python': install_python,
    'ruby': install_ruby,
    'node': install_node,
}


class Repository(object):
    def __init__(self, repo_config):
        self.repo_config = repo_config

    @cached_property
    def repo_url(self):
        return self.repo_config['repo']

    @cached_property
    def sha(self):
        return self.repo_config['sha']

    @cached_property
    def languages(self):
        return set(filter(None, (
            hook.get('language') for hook in self.hooks.values()
        )))

    @cached_property
    def hooks(self):
        return dict(
            (hook['id'], dict(hook, **self.manifest[hook['id']]))
            for hook in self.repo_config['hooks']
        )

    @cached_property
    def manifest(self):
        with self.in_checkout():
            return dict(
                (hook['id'], hook)
                for hook in validate_manifest(C.MANIFEST_FILE)
            )

    @contextlib.contextmanager
    def in_checkout(self):
        with in_hooks_workspace():
            # SMELL:
            self.create()
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
        with self.in_checkout():
            for language in C.SUPPORTED_LANGUAGES:
                if language in self.languages:
                    language_to_repo_setup_strategy[language](self)