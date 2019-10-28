from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os.path
import tarfile

from pre_commit import output
from pre_commit.util import cmd_output_b
from pre_commit.util import rmtree
from pre_commit.util import tmpdir


# This is a script for generating the tarred resources for git repo
# dependencies.  Currently it's just for "vendoring" ruby support packages.


REPOS = (
    ('rbenv', 'git://github.com/rbenv/rbenv', 'a3fa9b7'),
    ('ruby-build', 'git://github.com/rbenv/ruby-build', '1a902f3'),
    (
        'ruby-download',
        'git://github.com/garnieretienne/rvm-download',
        '09bd7c6',
    ),
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
        cmd_output_b('git', 'clone', repo, tempdir)
        cmd_output_b('git', 'checkout', ref, cwd=tempdir)

        # We don't want the '.git' directory
        # It adds a bunch of size to the archive and we don't use it at
        # runtime
        rmtree(os.path.join(tempdir, '.git'))

        with tarfile.open(output_path, 'w|gz') as tf:
            tf.add(tempdir, name)

    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', default='pre_commit/resources')
    args = parser.parse_args(argv)
    for archive_name, repo, ref in REPOS:
        output.write_line(
            'Making {}.tar.gz for {}@{}'.format(archive_name, repo, ref),
        )
        make_archive(archive_name, repo, ref, args.dest)


if __name__ == '__main__':
    exit(main())
