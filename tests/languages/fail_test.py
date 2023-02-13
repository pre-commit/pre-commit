from __future__ import annotations

from pre_commit.languages import fail
from testing.language_helpers import run_language


def test_fail_hooks(tmp_path):
    ret = run_language(
        tmp_path,
        fail,
        'watch out for',
        file_args=('bunnies',),
    )
    assert ret == (1, b'watch out for\n\nbunnies\n')
