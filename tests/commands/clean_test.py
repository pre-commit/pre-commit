import os.path
from unittest import mock

import pytest

from pre_commit.commands.clean import clean


@pytest.fixture(autouse=True)
def fake_old_dir(tempdir_factory):
    fake_old_dir = tempdir_factory.get()

    def _expanduser(path, *args, **kwargs):
        assert path == '~/.pre-commit'
        return fake_old_dir

    with mock.patch.object(os.path, 'expanduser', side_effect=_expanduser):
        yield fake_old_dir


def test_clean(store, fake_old_dir):
    assert os.path.exists(fake_old_dir)
    assert os.path.exists(store.directory)
    clean(store)
    assert not os.path.exists(fake_old_dir)
    assert not os.path.exists(store.directory)


def test_clean_idempotent(store):
    clean(store)
    assert not os.path.exists(store.directory)
    clean(store)
    assert not os.path.exists(store.directory)
