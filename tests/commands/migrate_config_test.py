from __future__ import annotations

import pytest

import pre_commit.constants as C
from pre_commit.clientlib import InvalidConfigError
from pre_commit.commands.migrate_config import migrate_config


def test_migrate_config_normal_format(tmpdir, capsys):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n',
    )
    with tmpdir.as_cwd():
        assert not migrate_config(C.CONFIG_FILE)
    out, _ = capsys.readouterr()
    assert out == 'Configuration has been migrated.\n'
    contents = cfg.read()
    assert contents == (
        'repos:\n'
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n'
    )


def test_migrate_config_document_marker(tmpdir):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        '# comment\n'
        '\n'
        '---\n'
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n',
    )
    with tmpdir.as_cwd():
        assert not migrate_config(C.CONFIG_FILE)
    contents = cfg.read()
    assert contents == (
        '# comment\n'
        '\n'
        '---\n'
        'repos:\n'
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n'
    )


def test_migrate_config_list_literal(tmpdir):
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(
        '[{\n'
        '    repo: local,\n'
        '    hooks: [{\n'
        '        id: foo, name: foo, entry: ./bin/foo.sh,\n'
        '        language: script,\n'
        '    }]\n'
        '}]',
    )
    with tmpdir.as_cwd():
        assert not migrate_config(C.CONFIG_FILE)
    contents = cfg.read()
    assert contents == (
        'repos:\n'
        '    [{\n'
        '        repo: local,\n'
        '        hooks: [{\n'
        '            id: foo, name: foo, entry: ./bin/foo.sh,\n'
        '            language: script,\n'
        '        }]\n'
        '    }]'
    )


def test_already_migrated_configuration_noop(tmpdir, capsys):
    contents = (
        'repos:\n'
        '-   repo: local\n'
        '    hooks:\n'
        '    -   id: foo\n'
        '        name: foo\n'
        '        entry: ./bin/foo.sh\n'
        '        language: script\n'
    )
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(contents)
    with tmpdir.as_cwd():
        assert not migrate_config(C.CONFIG_FILE)
    out, _ = capsys.readouterr()
    assert out == 'Configuration is already migrated.\n'
    assert cfg.read() == contents


def test_migrate_config_sha_to_rev(tmpdir):
    contents = (
        'repos:\n'
        '-   repo: https://github.com/pre-commit/pre-commit-hooks\n'
        '    sha: v1.2.0\n'
        '    hooks: []\n'
        '-   repo: https://github.com/pre-commit/pre-commit-hooks\n'
        '    sha: v1.2.0\n'
        '    hooks: []\n'
    )
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(contents)
    with tmpdir.as_cwd():
        assert not migrate_config(C.CONFIG_FILE)
    contents = cfg.read()
    assert contents == (
        'repos:\n'
        '-   repo: https://github.com/pre-commit/pre-commit-hooks\n'
        '    rev: v1.2.0\n'
        '    hooks: []\n'
        '-   repo: https://github.com/pre-commit/pre-commit-hooks\n'
        '    rev: v1.2.0\n'
        '    hooks: []\n'
    )


def test_migrate_config_sha_to_rev_json(tmp_path):
    contents = """\
{"repos": [{
    "repo": "https://github.com/pre-commit/pre-commit-hooks",
    "sha": "v1.2.0",
    "hooks": []
}]}
"""
    expected = """\
{"repos": [{
    "repo": "https://github.com/pre-commit/pre-commit-hooks",
    "rev": "v1.2.0",
    "hooks": []
}]}
"""
    cfg = tmp_path.joinpath('cfg.yaml')
    cfg.write_text(contents)
    assert not migrate_config(str(cfg))
    assert cfg.read_text() == expected


def test_migrate_config_language_python_venv(tmp_path):
    src = '''\
repos:
-   repo: local
    hooks:
    -   id: example
        name: example
        entry: example
        language: python_venv
    -   id: example
        name: example
        entry: example
        language: system
'''
    expected = '''\
repos:
-   repo: local
    hooks:
    -   id: example
        name: example
        entry: example
        language: python
    -   id: example
        name: example
        entry: example
        language: system
'''
    cfg = tmp_path.joinpath('cfg.yaml')
    cfg.write_text(src)
    assert migrate_config(str(cfg)) == 0
    assert cfg.read_text() == expected


def test_migrate_config_quoted_python_venv(tmp_path):
    src = '''\
repos:
-   repo: local
    hooks:
    -   id: example
        name: example
        entry: example
        language: "python_venv"
'''
    expected = '''\
repos:
-   repo: local
    hooks:
    -   id: example
        name: example
        entry: example
        language: "python"
'''
    cfg = tmp_path.joinpath('cfg.yaml')
    cfg.write_text(src)
    assert migrate_config(str(cfg)) == 0
    assert cfg.read_text() == expected


def test_migrate_config_default_stages(tmp_path):
    src = '''\
default_stages: [commit, push, merge-commit, commit-msg]
repos: []
'''
    expected = '''\
default_stages: [pre-commit, pre-push, pre-merge-commit, commit-msg]
repos: []
'''
    cfg = tmp_path.joinpath('cfg.yaml')
    cfg.write_text(src)
    assert migrate_config(str(cfg)) == 0
    assert cfg.read_text() == expected


def test_migrate_config_hook_stages(tmp_path):
    src = '''\
repos:
-   repo: local
    hooks:
    -   id: example
        name: example
        entry: example
        language: system
        stages: ["commit", "push", "merge-commit", "commit-msg"]
'''
    expected = '''\
repos:
-   repo: local
    hooks:
    -   id: example
        name: example
        entry: example
        language: system
        stages: ["pre-commit", "pre-push", "pre-merge-commit", "commit-msg"]
'''
    cfg = tmp_path.joinpath('cfg.yaml')
    cfg.write_text(src)
    assert migrate_config(str(cfg)) == 0
    assert cfg.read_text() == expected


def test_migrate_config_invalid_yaml(tmpdir):
    contents = '['
    cfg = tmpdir.join(C.CONFIG_FILE)
    cfg.write(contents)
    with tmpdir.as_cwd(), pytest.raises(InvalidConfigError) as excinfo:
        migrate_config(C.CONFIG_FILE)
    expected = '\n==> File .pre-commit-config.yaml\n=====> '
    assert str(excinfo.value).startswith(expected)
