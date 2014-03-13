import os
import pkg_resources
import contextlib

import pre_commit.constants as C
from plumbum import local


def get_root():
    return local['git']['rev-parse', '--show-toplevel']().strip()


def get_pre_commit_path():
    return os.path.join(get_root(), '.git/hooks/pre-commit')


def get_pre_commit_dir_path():
    return os.path.join(get_root(), C.PRE_COMMIT_DIR)

def create_pre_commit_package_dir():
    local.path(get_pre_commit_dir_path()).mkdir()

def create_pre_commit():
    path = get_pre_commit_path()
    pre_commit_file = pkg_resources.resource_filename('pre_commit', 'resources/pre-commit.sh')
    local.path(path).write(local.path(pre_commit_file).read())


def remove_pre_commit():
    local.path(get_pre_commit_path()).delete()


class PreCommitProject(object):

    def __init__(self, git_repo_path, sha):
        self.git_repo_path = git_repo_path
        self.sha = sha

    @contextlib.contextmanager
    def in_checkout(self):
        with local.cwd(get_pre_commit_dir_path()):
            with local.cwd(self.sha):
                yield

    def create(self):
        create_pre_commit_package_dir()

        with local.cwd(get_pre_commit_dir_path()):
            local['git']['clone', self.git_repo_path, self.sha]()
            with self.in_checkout():
                local['git']['checkout', self.sha]()

    def install(self):
        with self.in_checkout():
            if local.path('setup.py').exists():
                local['virtualenv']['py_env']()
                local['bash']['-c', 'source py_env/bin/activate && pip install .']()
                print local.cwd.getpath()

def create_repo_in_env(git_repo_path, sha):
    project = PreCommitProject(git_repo_path, sha)
    project.create()

def install_pre_commit(git_repo_path, sha):
    project = PreCommitProject(git_repo_path, sha)
    project.create()
    project.install()


