from __future__ import annotations

from pre_commit.languages import script
from pre_commit.util import make_executable
from testing.language_helpers import run_language


def test_script_language(tmp_path):
    exe = tmp_path.joinpath('main')
    exe.write_text('#!/usr/bin/env bash\necho hello hello world\n')
    make_executable(exe)

    expected = (0, b'hello hello world\n')
    assert run_language(tmp_path, script, 'main') == expected
