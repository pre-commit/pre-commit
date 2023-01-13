from __future__ import annotations

import re
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit.languages import golang
from pre_commit.languages import helpers


ACTUAL_GET_DEFAULT_VERSION = golang.get_default_version.__wrapped__


@pytest.fixture
def exe_exists_mck():
    with mock.patch.object(helpers, 'exe_exists') as mck:
        yield mck


def test_golang_default_version_system_available(exe_exists_mck):
    exe_exists_mck.return_value = True
    assert ACTUAL_GET_DEFAULT_VERSION() == 'system'


def test_golang_default_version_system_not_available(exe_exists_mck):
    exe_exists_mck.return_value = False
    assert ACTUAL_GET_DEFAULT_VERSION() == C.DEFAULT


ACTUAL_INFER_GO_VERSION = golang._infer_go_version.__wrapped__


def test_golang_infer_go_version_not_default():
    assert ACTUAL_INFER_GO_VERSION('1.19.4') == '1.19.4'


def test_golang_infer_go_version_default():
    version = ACTUAL_INFER_GO_VERSION(C.DEFAULT)

    assert version != C.DEFAULT
    assert re.match(r'^\d+\.\d+\.\d+$', version)
