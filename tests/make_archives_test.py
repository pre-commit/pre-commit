from __future__ import absolute_import
from __future__ import unicode_literals

import os.path
import tarfile

import mock
import pytest

from pre_commit import make_archives
from pre_commit.util import cmd_output
from pre_commit.util import cwd
from testing.fixtures import git_dir
from testing.util import get_head_sha
from testing.util import skipif_slowtests_false


def test_make_archive(tempdir_factory):
    output_dir = tempdir_factory.get()
    git_path = git_dir(tempdir_factory)
    # Add a files to the git directory
    with cwd(git_path):
        open('foo', 'a').close()
        cmd_output('git', 'add', '.')
        cmd_output('git', 'commit', '-m', 'foo')
        # We'll use this sha
        head_sha = get_head_sha('.')
        # And check that this file doesn't exist
        open('bar', 'a').close()
        cmd_output('git', 'add', '.')
        cmd_output('git', 'commit', '-m', 'bar')

    # Do the thing
    archive_path = make_archives.make_archive(
        'foo', git_path, head_sha, output_dir,
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


@skipif_slowtests_false
@pytest.mark.integration
def test_main(tempdir_factory):
    path = tempdir_factory.get()

    # Don't actually want to make these in the current repo
    with mock.patch.object(make_archives, 'RESOURCES_DIR', path):
        make_archives.main()

    for archive, _, _ in make_archives.REPOS:
        assert os.path.exists(os.path.join(path, archive + '.tar.gz'))
