from __future__ import annotations

from pre_commit.commands.validate_manifest import validate_manifest


def test_validate_manifest_ok():
    assert not validate_manifest(('.pre-commit-hooks.yaml',))


def test_not_ok(tmpdir):
    not_yaml = tmpdir.join('f.notyaml')
    not_yaml.write('{')
    not_schema = tmpdir.join('notconfig.yaml')
    not_schema.write('{}')

    assert validate_manifest(('does-not-exist',))
    assert validate_manifest((not_yaml.strpath,))
    assert validate_manifest((not_schema.strpath,))
