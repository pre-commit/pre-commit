from __future__ import absolute_import
from __future__ import unicode_literals

import mock
import os.path
import pytest
from plumbum import local

from pre_commit import make_archives
from pre_commit.util import tarfile_open
from testing.fixtures import git_dir
from testing.util import get_head_sha
from testing.util import skipif_slowtests_false


def test_make_archive(tmpdir_factory):
    output_dir = tmpdir_factory.get()
    git_path = git_dir(tmpdir_factory)
    # Add a files to the git directory
    with local.cwd(git_path):
        local['touch']('foo')
        local['git']('add', '.')
        local['git']('commit', '-m', 'foo')
        # We'll use this sha
        head_sha = get_head_sha('.')
        # And check that this file doesn't exist
        local['touch']('bar')
        local['git']('add', '.')
        local['git']('commit', '-m', 'bar')

    # Do the thing
    archive_path = make_archives.make_archive(
        'foo', git_path, head_sha, output_dir,
    )

    assert archive_path == os.path.join(output_dir, 'foo.tar.gz')
    assert os.path.exists(archive_path)

    extract_dir = tmpdir_factory.get()

    # Extract the tar
    with tarfile_open(archive_path) as tf:
        tf.extractall(extract_dir)

    # Verify the contents of the tar
    assert os.path.exists(os.path.join(extract_dir, 'foo'))
    assert os.path.exists(os.path.join(extract_dir, 'foo', 'foo'))
    assert not os.path.exists(os.path.join(extract_dir, 'foo', '.git'))
    assert not os.path.exists(os.path.join(extract_dir, 'foo', 'bar'))


@skipif_slowtests_false
@pytest.mark.integration
def test_main(tmpdir_factory):
    path = tmpdir_factory.get()

    # Don't actually want to make these in the current repo
    with mock.patch.object(make_archives, 'RESOURCES_DIR', path):
        make_archives.main()

    for archive, _, _ in make_archives.REPOS:
        assert os.path.exists(os.path.join(path, archive + '.tar.gz'))
