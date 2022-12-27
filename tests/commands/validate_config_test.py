from __future__ import annotations

import logging

from pre_commit.commands.validate_config import validate_config


def test_validate_config_ok():
    assert not validate_config(('.pre-commit-config.yaml',))


def test_validate_warn_on_unknown_keys_at_repo_level(tmpdir, caplog):
    f = tmpdir.join('cfg.yaml')
    f.write(
        'repos:\n'
        '-   repo: https://gitlab.com/pycqa/flake8\n'
        '    rev: 3.7.7\n'
        '    hooks:\n'
        '    -   id: flake8\n'
        '    args: [--some-args]\n',
    )
    ret_val = validate_config((f.strpath,))
    assert not ret_val
    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            'Unexpected key(s) present on https://gitlab.com/pycqa/flake8: '
            'args',
        ),
    ]


def test_validate_warn_on_unknown_keys_at_top_level(tmpdir, caplog):
    f = tmpdir.join('cfg.yaml')
    f.write(
        'repos:\n'
        '-   repo: https://gitlab.com/pycqa/flake8\n'
        '    rev: 3.7.7\n'
        '    hooks:\n'
        '    -   id: flake8\n'
        'foo:\n'
        '    id: 1.0.0\n',
    )
    ret_val = validate_config((f.strpath,))
    assert not ret_val
    assert caplog.record_tuples == [
        (
            'pre_commit',
            logging.WARNING,
            'Unexpected key(s) present at root: foo',
        ),
    ]


def test_mains_not_ok(tmpdir):
    not_yaml = tmpdir.join('f.notyaml')
    not_yaml.write('{')
    not_schema = tmpdir.join('notconfig.yaml')
    not_schema.write('{}')

    assert validate_config(('does-not-exist',))
    assert validate_config((not_yaml.strpath,))
    assert validate_config((not_schema.strpath,))
