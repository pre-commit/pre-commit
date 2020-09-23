import argparse
import os.path
import tarfile
from typing import Optional
from typing import Sequence

from pre_commit import output
from pre_commit.util import cmd_output_b
from pre_commit.util import rmtree
from pre_commit.util import tmpdir


# This is a script for generating the tarred resources for git repo
# dependencies.  Currently it's just for "vendoring" ruby support packages.


REPOS = (
    ('rbenv', 'git://github.com/rbenv/rbenv', '0843745'),
    ('ruby-build', 'git://github.com/rbenv/ruby-build', '258455e'),
    (
        'ruby-download',
        'git://github.com/garnieretienne/rvm-download',
        '09bd7c6',
    ),
)


def make_archive(name: str, repo: str, ref: str, destdir: str) -> str:
    """Makes an archive of a repository in the given destdir.

    :param text name: Name to give the archive.  For instance foo.  The file
    that is created will be called foo.tar.gz.
    :param text repo: Repository to clone.
    :param text ref: Tag/SHA/branch to check out.
    :param text destdir: Directory to place archives in.
    """
    output_path = os.path.join(destdir, f'{name}.tar.gz')
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


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', default='pre_commit/resources')
    args = parser.parse_args(argv)
    for archive_name, repo, ref in REPOS:
        output.write_line(f'Making {archive_name}.tar.gz for {repo}@{ref}')
        make_archive(archive_name, repo, ref, args.dest)
    return 0


if __name__ == '__main__':
    exit(main())
