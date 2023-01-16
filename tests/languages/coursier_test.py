from __future__ import annotations

import pytest

from pre_commit.errors import FatalError
from pre_commit.languages import coursier
from testing.language_helpers import run_language


def test_coursier_hook(tmp_path):
    echo_java_json = '''\
{
  "repositories": ["central"],
  "dependencies": ["io.get-coursier:echo:latest.stable"]
}
'''

    channel_dir = tmp_path.joinpath('.pre-commit-channel')
    channel_dir.mkdir()
    channel_dir.joinpath('echo-java.json').write_text(echo_java_json)

    ret = run_language(
        tmp_path,
        coursier,
        'echo-java',
        args=('Hello', 'World', 'from', 'coursier'),
    )
    assert ret == (0, b'Hello World from coursier\n')


def test_coursier_hook_additional_dependencies(tmp_path):
    ret = run_language(
        tmp_path,
        coursier,
        'scalafmt --version',
        deps=('scalafmt:3.6.1',),
    )
    assert ret == (0, b'scalafmt 3.6.1\n')


def test_error_if_no_deps_or_channel(tmp_path):
    with pytest.raises(FatalError) as excinfo:
        run_language(tmp_path, coursier, 'dne')
    msg, = excinfo.value.args
    assert msg == 'expected .pre-commit-channel dir or additional_dependencies'
