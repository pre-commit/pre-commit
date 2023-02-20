from __future__ import annotations

from pre_commit.languages import system
from testing.language_helpers import run_language


def test_system_language(tmp_path):
    expected = (0, b'hello hello world\n')
    assert run_language(tmp_path, system, 'echo hello hello world') == expected
