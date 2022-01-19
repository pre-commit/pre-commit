from __future__ import annotations

import pytest

from pre_commit import envcontext
from pre_commit.languages.conda import _conda_exe


@pytest.mark.parametrize(
    ('ctx', 'expected'),
    (
        pytest.param(
            (
                ('PRE_COMMIT_USE_MICROMAMBA', envcontext.UNSET),
                ('PRE_COMMIT_USE_MAMBA', envcontext.UNSET),
            ),
            'conda',
            id='default',
        ),
        pytest.param(
            (
                ('PRE_COMMIT_USE_MICROMAMBA', '1'),
                ('PRE_COMMIT_USE_MAMBA', ''),
            ),
            'micromamba',
            id='default',
        ),
        pytest.param(
            (
                ('PRE_COMMIT_USE_MICROMAMBA', ''),
                ('PRE_COMMIT_USE_MAMBA', '1'),
            ),
            'mamba',
            id='default',
        ),
    ),
)
def test_conda_exe(ctx, expected):
    with envcontext.envcontext(ctx):
        assert _conda_exe() == expected
