from __future__ import annotations

from pre_commit.languages import docker_image
from testing.language_helpers import run_language
from testing.util import xfailif_windows


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
