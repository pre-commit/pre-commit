import os
import pkg_resources
from plumbum import local


def get_root():
    return local['git']['rev-parse', '--show-toplevel']().strip()


def get_pre_commit_path():
    return os.path.join(get_root(), '.git/hooks/pre-commit')


def create_pre_commit():
    path = get_pre_commit_path()
    pre_commit_file = pkg_resources.resource_filename('pre_commit', 'resources/pre-commit.sh')
    local.path(path).write(local.path(pre_commit_file).read())


def remove_pre_commit():
    local.path(get_pre_commit_path()).delete()






