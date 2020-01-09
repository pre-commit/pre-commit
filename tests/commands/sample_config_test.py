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
    rev: v2.4.0
    hooks:
    -   id: trailing-whitespace
    -   id: end-of-file-fixer
    -   id: check-yaml
    -   id: check-added-large-files
'''
