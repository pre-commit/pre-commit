from __future__ import annotations

from pre_commit.languages import unsupported
from testing.language_helpers import run_language


def test_unsupported_language(tmp_path):
    expected = (0, b'hello hello world\n')
    ret = run_language(tmp_path, unsupported, 'echo hello hello world')
    assert ret == expected
