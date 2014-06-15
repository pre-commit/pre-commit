from __future__ import absolute_import
from __future__ import unicode_literals

from plumbum import local


git = local['git']


def git_dir(tmpdir_factory):
    path = tmpdir_factory.get()
    with local.cwd(path):
        git('init')
    return path
