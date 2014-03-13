import os
import pkg_resources
from plumbum import local


def get_root():
    return local['git']['rev-parse', '--show-toplevel']().strip()


def get_pre_commit_path():
    return os.path.join(get_root(), '.git/hooks/pre-commit')


def get_env_path():
    return os.path.join(get_root(), '.pre-commit')

def create_pre_commit_package_dir():
    local.path(get_root() + '/.pre-commit').mkdir()

def create_pre_commit():
    path = get_pre_commit_path()
    pre_commit_file = pkg_resources.resource_filename('pre_commit', 'resources/pre-commit.sh')
    local.path(path).write(local.path(pre_commit_file).read())


def remove_pre_commit():
    local.path(get_pre_commit_path()).delete()

def create_repo_in_env(name, git_repo_path):
    create_pre_commit_package_dir()

    env_path = get_env_path()

    with local.cwd(env_path):
        local['git']['clone', git_repo_path, name]()
        print local.cwd.getpath()
