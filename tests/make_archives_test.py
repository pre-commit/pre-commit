from __future__ import absolute_import
from __future__ import unicode_literals

import os.path
import tarfile

import pytest

from pre_commit import git
from pre_commit import make_archives
from pre_commit.util import cmd_output
from testing.fixtures import git_dir


def test_make_archive(tempdir_factory):
    output_dir = tempdir_factory.get()
    git_path = git_dir(tempdir_factory)
    # Add a files to the git directory
    open(os.path.join(git_path, 'foo'), 'a').close()
    cmd_output('git', 'add', '.', cwd=git_path)
    cmd_output('git', 'commit', '-m', 'foo', cwd=git_path)
    # We'll use this rev
    head_rev = git.head_rev(git_path)
    # And check that this file doesn't exist
    open(os.path.join(git_path, 'bar'), 'a').close()
    cmd_output('git', 'add', '.', cwd=git_path)
    cmd_output('git', 'commit', '-m', 'bar', cwd=git_path)

    # Do the thing
    archive_path = make_archives.make_archive(
        'foo', git_path, head_rev, output_dir,
    )

    assert archive_path == os.path.join(output_dir, 'foo.tar.gz')
    assert os.path.exists(archive_path)

    extract_dir = tempdir_factory.get()

    # Extract the tar
    with tarfile.open(archive_path) as tf:
        tf.extractall(extract_dir)

    # Verify the contents of the tar
    assert os.path.exists(os.path.join(extract_dir, 'foo'))
    assert os.path.exists(os.path.join(extract_dir, 'foo', 'foo'))
    assert not os.path.exists(os.path.join(extract_dir, 'foo', '.git'))
    assert not os.path.exists(os.path.join(extract_dir, 'foo', 'bar'))


@pytest.mark.integration
def test_main(tmpdir):
    make_archives.main(('--dest', tmpdir.strpath))

    for archive, _, _ in make_archives.REPOS:
        assert tmpdir.join('{}.tar.gz'.format(archive)).exists()
