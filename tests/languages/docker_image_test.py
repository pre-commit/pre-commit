from __future__ import annotations

import pytest

from pre_commit.languages import docker_image
from pre_commit.util import cmd_output_b
from testing.language_helpers import run_language
from testing.util import xfailif_windows


@pytest.fixture(autouse=True, scope='module')
def _ensure_image_available():
    cmd_output_b('docker', 'run', '--rm', 'ubuntu:22.04', 'echo')


@xfailif_windows  # pragma: win32 no cover
def test_docker_image_hook_via_entrypoint(tmp_path):
    ret = run_language(
        tmp_path,
        docker_image,
        '--entrypoint echo ubuntu:22.04',
        args=('hello hello world',),
    )
    assert ret == (0, b'hello hello world\n')


@xfailif_windows  # pragma: win32 no cover
def test_docker_image_hook_via_args(tmp_path):
    ret = run_language(
        tmp_path,
        docker_image,
        'ubuntu:22.04 echo',
        args=('hello hello world',),
    )
    assert ret == (0, b'hello hello world\n')


@xfailif_windows  # pragma: win32 no cover
def test_docker_image_color_tty(tmp_path):
    ret = run_language(
        tmp_path,
        docker_image,
        'ubuntu:22.04',
        args=('grep', '--color', 'root', '/etc/group'),
        color=True,
    )
    assert ret == (0, b'\x1b[01;31m\x1b[Kroot\x1b[m\x1b[K:x:0:\n')


@xfailif_windows  # pragma: win32 no cover
def test_docker_image_no_color_no_tty(tmp_path):
    ret = run_language(
        tmp_path,
        docker_image,
        'ubuntu:22.04',
        args=('grep', '--color', 'root', '/etc/group'),
        color=False,
    )
    assert ret == (0, b'root:x:0:\n')
