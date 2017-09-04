from __future__ import unicode_literals

import os.path

import mock
import pytest

from pre_commit.commands.clean import clean
from pre_commit.util import rmtree


@pytest.fixture(autouse=True)
def fake_old_dir(tempdir_factory):
    fake_old_dir = tempdir_factory.get()

    def _expanduser(path, *args, **kwargs):
        assert path == '~/.pre-commit'
        return fake_old_dir

    with mock.patch.object(os.path, 'expanduser', side_effect=_expanduser):
        yield fake_old_dir


def test_clean(runner_with_mocked_store, fake_old_dir):
    assert os.path.exists(fake_old_dir)
    assert os.path.exists(runner_with_mocked_store.store.directory)
    clean(runner_with_mocked_store)
    assert not os.path.exists(fake_old_dir)
    assert not os.path.exists(runner_with_mocked_store.store.directory)


def test_clean_empty(runner_with_mocked_store):
    """Make sure clean succeeds when the directory doesn't exist."""
    rmtree(runner_with_mocked_store.store.directory)
    assert not os.path.exists(runner_with_mocked_store.store.directory)
    clean(runner_with_mocked_store)
    assert not os.path.exists(runner_with_mocked_store.store.directory)
