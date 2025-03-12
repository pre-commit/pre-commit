from __future__ import annotations

from pre_commit.commands.sample_config import sample_config


def test_sample_config(capsys):
    ret = sample_config()
    assert ret == 0
    out, _ = capsys.readouterr()
    assert out == '''\
# See https://pre-commit.com for more information
# See https://pre-commit.com/hooks.html for more hooks
repos:
-   repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v3.2.0 # do not make PR to pre-commit/pre-commit to update this
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
'''
