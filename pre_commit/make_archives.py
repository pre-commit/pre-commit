from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import os.path

from pre_commit import five
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from pre_commit.util import rmtree
from pre_commit.util import tarfile_open
from pre_commit.util import tmpdir


# This is a script for generating the tarred resources for git repo
# dependencies.  Currently it's just for "vendoring" ruby support packages.


REPOS = (
    ('rbenv', 'git://github.com/sstephenson/rbenv', '13a474c'),
    ('ruby-build', 'git://github.com/sstephenson/ruby-build', 'd3d5fe0'),
    (
        'ruby-download',
        'git://github.com/garnieretienne/rvm-download',
        'f2e9f1e',
    ),
)


RESOURCES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'resources')
)


def make_archive(name, repo, ref, destdir):
    """Makes an archive of a repository in the given destdir.

    :param text name: Name to give the archive.  For instance foo.  The file
    that is created will be called foo.tar.gz.
    :param text repo: Repository to clone.
    :param text ref: Tag/SHA/branch to check out.
    :param text destdir: Directory to place archives in.
    """
    output_path = os.path.join(destdir, name + '.tar.gz')
    with tmpdir() as tempdir:
        # Clone the repository to the temporary directory
        cmd_output('git', 'clone', repo, tempdir)
        with cwd(tempdir):
            cmd_output('git', 'checkout', ref)

        # We don't want the '.git' directory
        # It adds a bunch of size to the archive and we don't use it at
        # runtime
        rmtree(os.path.join(tempdir, '.git'))

        with tarfile_open(five.n(output_path), 'w|gz') as tf:
            tf.add(tempdir, name)

    return output_path


def main():
    for archive_name, repo, ref in REPOS:
        print('Making {0}.tar.gz for {1}@{2}'.format(archive_name, repo, ref))
        make_archive(archive_name, repo, ref, RESOURCES_DIR)


if __name__ == '__main__':
    exit(main())
