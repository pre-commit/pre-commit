from __future__ import annotations

from itertools import product
from pathlib import Path
from typing import Any

import pytest

from pre_commit.hook import Hook
from pre_commit.languages import sbt
from testing.util import cwd
from testing.util import skipif_cant_run_sbt


@skipif_cant_run_sbt
@pytest.mark.parametrize(
    ['args', 'files'],
    product(
        [
            [], ['argfile1.txt'], ['argfile1.txt', 'argfile2.txt'],
            ['\"arg file1.txt\"'], ['\"arg file1.txt\"', '\"arg file2.txt\"'],
        ],
        [
            [], ['filesfile1.txt'], ['filesfile1.txt', 'filesfile2.txt'],
            ['files file1.txt'], ['files file1.txt', 'files file2.txt'],
        ],
    ),
)
def test_sbt_hook(
        sbt_project_with_touch_command: Path,
        args: list[str],
        files: list[str],
) -> None:
    # arrange
    project_root = sbt_project_with_touch_command
    hook = _create_hook(
        language='sbt',
        entry='touch',
        args=args,
    )

    # act
    with cwd(project_root):
        ret, out = sbt.run_hook(hook, files, False)

    # assert
    output = out.decode('UTF-8')
    assert ret == 0
    for file in args + files:
        unquoted_file = _unquote(file)
        expected_file = project_root.joinpath(unquoted_file).absolute()
        assert expected_file.exists()
        assert f'Creating file: {expected_file}' in output


def _unquote(s: str) -> str:
    return s.strip("\"")


def _create_hook(**kwargs: Any) -> Hook:
    default_values = {field: None for field in Hook._fields}
    actual_values = {**default_values, **kwargs}
    return Hook(**actual_values)  # type: ignore
