import contextlib

from plumbum import local
from pre_commit import git

class RepoInstaller(object):

    def __init__(self, git_repo_path, sha):
        self.git_repo_path = git_repo_path
        self.sha = sha

    @contextlib.contextmanager
    def in_checkout(self):
        with local.cwd(git.get_pre_commit_dir_path()):
            with local.cwd(self.sha):
                yield

    def create(self):
        git.create_pre_commit_package_dir()

        with local.cwd(git.get_pre_commit_dir_path()):
            if local.path(self.sha).exists():
                # Project already exists, no reason to re-create it
                return

            local['git']['clone', self.git_repo_path, self.sha]()
            with self.in_checkout():
                local['git']['checkout', self.sha]()

    def install(self):
        with self.in_checkout():
            if local.path('setup.py').exists():
                local['virtualenv']['py_env']()
                local['bash']['-c', 'source py_env/bin/activate && pip install .']()


def create_repo_in_env(git_repo_path, sha):
    project = RepoInstaller(git_repo_path, sha)
    project.create()

def install_pre_commit(git_repo_path, sha):
    project = RepoInstaller(git_repo_path, sha)
    project.create()
    project.install()