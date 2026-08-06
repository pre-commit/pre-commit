from __future__ import annotations

import shutil
from unittest import mock

import pytest

import pre_commit.constants as C
from pre_commit.languages import deno
from pre_commit.prefix import Prefix
from testing.language_helpers import run_language


def test_default_version():
    assert deno.get_default_version() == C.DEFAULT


def test_healthy_deno():
    with mock.patch.object(deno, 'cmd_output_b', return_value=(0, b'', b'')):
        assert deno.health_check(Prefix('/tmp'), C.DEFAULT) is None


def test_unhealthy_deno():
    with mock.patch.object(deno, 'cmd_output_b', return_value=(127, b'', b'')):
        assert deno.health_check(Prefix('/tmp'), C.DEFAULT) == '`deno --version` returned 127'


def test_rejects_version():
    with pytest.raises(AssertionError, match='system-installed deno'):
        deno.install_environment(Prefix('/tmp'), '2.0.0', ())


def test_rejects_additional_dependencies():
    with pytest.raises(AssertionError, match='additional_dependencies'):
        deno.install_environment(Prefix('/tmp'), C.DEFAULT, ('npm:typescript',))


@pytest.mark.skipif(shutil.which('deno') is None, reason='deno is not installed')
def test_deno_hook():
    assert run_language(
        Prefix('/tmp').prefix_dir,
        deno,
        'deno eval \'console.log("hello from deno")\'',
    ) == (0, b'hello from deno\n')
