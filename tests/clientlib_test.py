from __future__ import unicode_literals

import pytest

from pre_commit import schema
from pre_commit.clientlib import check_language
from pre_commit.clientlib import check_type_tag
from pre_commit.clientlib import CONFIG_HOOK_DICT
from pre_commit.clientlib import CONFIG_SCHEMA
from pre_commit.clientlib import is_local_repo
from pre_commit.clientlib import MANIFEST_SCHEMA
from pre_commit.clientlib import validate_config_main
from pre_commit.clientlib import validate_manifest_main
from testing.util import get_resource_path


def is_valid_according_to_schema(obj, obj_schema):
    try:
        schema.validate(obj, obj_schema)
        return True
    except schema.ValidationError:
        return False


@pytest.mark.parametrize('value', ('not a language', 'python3'))
def test_check_language_failures(value):
    with pytest.raises(schema.ValidationError):
        check_language(value)


@pytest.mark.parametrize('value', ('definitely-not-a-tag', 'fiel'))
def test_check_type_tag_failures(value):
    with pytest.raises(schema.ValidationError):
        check_type_tag(value)


@pytest.mark.parametrize('value', ('python', 'node', 'pcre'))
def test_check_language_ok(value):
    check_language(value)


def test_is_local_repo():
    assert is_local_repo({'repo': 'local'})


@pytest.mark.parametrize(
    ('args', 'expected_output'),
    (
        (['.pre-commit-config.yaml'], 0),
        (['non_existent_file.yaml'], 1),
        ([get_resource_path('valid_yaml_but_invalid_config.yaml')], 1),
        ([get_resource_path('non_parseable_yaml_file.notyaml')], 1),
    ),
)
def test_validate_config_main(args, expected_output):
    assert validate_config_main(args) == expected_output


@pytest.mark.parametrize(('config_obj', 'expected'), (
    ([], False),
    (
        [{
            'repo': 'git@github.com:pre-commit/pre-commit-hooks',
            'sha': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
            'hooks': [{'id': 'pyflakes', 'files': '\\.py$'}],
        }],
        True,
    ),
    (
        [{
            'repo': 'git@github.com:pre-commit/pre-commit-hooks',
            'sha': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
            'hooks': [
                {
                    'id': 'pyflakes',
                    'files': '\\.py$',
                    'args': ['foo', 'bar', 'baz'],
                },
            ],
        }],
        True,
    ),
    (
        [{
            'repo': 'git@github.com:pre-commit/pre-commit-hooks',
            'sha': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
            'hooks': [
                {
                    'id': 'pyflakes',
                    'files': '\\.py$',
                    # Exclude pattern must be a string
                    'exclude': 0,
                    'args': ['foo', 'bar', 'baz'],
                },
            ],
        }],
        False,
    ),
))
def test_config_valid(config_obj, expected):
    ret = is_valid_according_to_schema(config_obj, CONFIG_SCHEMA)
    assert ret is expected


@pytest.mark.parametrize('config_obj', (
    [{
        'repo': 'local',
        'sha': 'foo',
        'hooks': [{
            'id': 'do_not_commit',
            'name': 'Block if "DO NOT COMMIT" is found',
            'entry': 'DO NOT COMMIT',
            'language': 'pcre',
            'files': '^(.*)$',
        }],
    }],
))
def test_config_with_local_hooks_definition_fails(config_obj):
    with pytest.raises(schema.ValidationError):
        schema.validate(config_obj, CONFIG_SCHEMA)


@pytest.mark.parametrize('config_obj', (
    [{
        'repo': 'local',
        'hooks': [{
            'id': 'arg-per-line',
            'name': 'Args per line hook',
            'entry': 'bin/hook.sh',
            'language': 'script',
            'files': '',
            'args': ['hello', 'world'],
        }],
    }],
    [{
        'repo': 'local',
        'hooks': [{
            'id': 'arg-per-line',
            'name': 'Args per line hook',
            'entry': 'bin/hook.sh',
            'language': 'script',
            'files': '',
            'args': ['hello', 'world'],
        }]
    }],
))
def test_config_with_local_hooks_definition_passes(config_obj):
    schema.validate(config_obj, CONFIG_SCHEMA)


def test_config_schema_does_not_contain_defaults():
    """Due to the way our merging works, if this schema has any defaults they
    will clobber potentially useful values in the backing manifest. #227
    """
    for item in CONFIG_HOOK_DICT.items:
        assert not isinstance(item, schema.Optional)


@pytest.mark.parametrize(
    ('args', 'expected_output'),
    (
        (['.pre-commit-hooks.yaml'], 0),
        (['non_existent_file.yaml'], 1),
        ([get_resource_path('valid_yaml_but_invalid_manifest.yaml')], 1),
        ([get_resource_path('non_parseable_yaml_file.notyaml')], 1),
    ),
)
def test_validate_manifest_main(args, expected_output):
    assert validate_manifest_main(args) == expected_output


@pytest.mark.parametrize(
    ('manifest_obj', 'expected'),
    (
        ([], False),
        (
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'files': r'\.py$'
            }],
            True,
        ),
        (
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'language_version': 'python3.4',
                'files': r'\.py$',
            }],
            True,
        ),
        (
            # A regression in 0.13.5: always_run and files are permissible
            # together (but meaningless).  In a future version upgrade this to
            # an error
            [{
                'id': 'a',
                'name': 'b',
                'entry': 'c',
                'language': 'python',
                'files': '',
                'always_run': True,
            }],
            True,
        ),
    )
)
def test_valid_manifests(manifest_obj, expected):
    ret = is_valid_according_to_schema(manifest_obj, MANIFEST_SCHEMA)
    assert ret is expected
