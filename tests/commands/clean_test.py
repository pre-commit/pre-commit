# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os.path

from pre_commit.commands.clean import clean
from pre_commit.util import rmtree


def test_clean(runner_with_mocked_store):
    assert os.path.exists(runner_with_mocked_store.store.directory)
    clean(runner_with_mocked_store)
    assert not os.path.exists(runner_with_mocked_store.store.directory)


def test_clean_empty(runner_with_mocked_store):
    """Make sure clean succeeds when we the directory doesn't exist."""
    rmtree(runner_with_mocked_store.store.directory)
    assert not os.path.exists(runner_with_mocked_store.store.directory)
    clean(runner_with_mocked_store)
    assert not os.path.exists(runner_with_mocked_store.store.directory)
