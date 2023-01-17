from __future__ import annotations

import os.path

import pytest

from pre_commit import envcontext
from pre_commit.languages import conda
from pre_commit.store import _make_local_repo
from testing.language_helpers import run_language


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
        assert conda._conda_exe() == expected


def test_conda_language(tmp_path):
    environment_yml = '''\
channels: [conda-forge, defaults]
dependencies: [python, pip]
'''
    tmp_path.joinpath('environment.yml').write_text(environment_yml)

    ret, out = run_language(
        tmp_path,
        conda,
        'python -c "import sys; print(sys.prefix)"',
    )
    assert ret == 0
    assert os.path.basename(out.strip()) == b'conda-default'


def test_conda_additional_deps(tmp_path):
    _make_local_repo(tmp_path)

    ret = run_language(
        tmp_path,
        conda,
        'python -c "import botocore; print(1)"',
        deps=('botocore',),
    )
    assert ret == (0, b'1\n')
