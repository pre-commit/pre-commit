from __future__ import unicode_literals

import jsonschema
import pytest

from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import InvalidConfigError
from pre_commit.clientlib.validate_config import run
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from testing.util import get_resource_path
from testing.util import is_valid_according_to_schema


@pytest.mark.parametrize(
    ('input', 'expected_output'),
    (
        (['.pre-commit-config.yaml'], 0),
        (['non_existent_file.yaml'], 1),
        ([get_resource_path('valid_yaml_but_invalid_config.yaml')], 1),
        ([get_resource_path('non_parseable_yaml_file.notyaml')], 1),
    ),
)
def test_run(input, expected_output):
    assert run(input) == expected_output


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
def test_is_valid_according_to_schema(config_obj, expected):
    ret = is_valid_according_to_schema(config_obj, CONFIG_JSON_SCHEMA)
    assert ret is expected


def test_config_with_failing_regexes_fails():
    with pytest.raises(InvalidConfigError):
        # Note the regex '(' is invalid (unbalanced parens)
        config = apply_defaults(
            [{
                'repo': 'foo',
                'sha': 'foo',
                'hooks': [{'id': 'hook_id', 'files': '('}],
            }],
            CONFIG_JSON_SCHEMA,
        )
        validate_config_extra(config)


def test_config_with_ok_regexes_passes():
    config = apply_defaults(
        [{
            'repo': 'foo',
            'sha': 'foo',
            'hooks': [{'id': 'hook_id', 'files': '\\.py$'}],
        }],
        CONFIG_JSON_SCHEMA,
    )
    validate_config_extra(config)


def test_config_with_invalid_exclude_regex_fails():
    with pytest.raises(InvalidConfigError):
        # Note the regex '(' is invalid (unbalanced parens)
        config = apply_defaults(
            [{
                'repo': 'foo',
                'sha': 'foo',
                'hooks': [{'id': 'hook_id', 'files': '', 'exclude': '('}],
            }],
            CONFIG_JSON_SCHEMA,
        )
        validate_config_extra(config)


def test_config_with_ok_exclude_regex_passes():
    config = apply_defaults(
        [{
            'repo': 'foo',
            'sha': 'foo',
            'hooks': [{'id': 'hook_id', 'files': '', 'exclude': '^vendor/'}],
        }],
        CONFIG_JSON_SCHEMA,
    )
    validate_config_extra(config)


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
    with pytest.raises((
        jsonschema.exceptions.ValidationError, InvalidConfigError
    )):
        jsonschema.validate(config_obj, CONFIG_JSON_SCHEMA)
        config = apply_defaults(config_obj, CONFIG_JSON_SCHEMA)
        validate_config_extra(config)


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
    jsonschema.validate(config_obj, CONFIG_JSON_SCHEMA)
    config = apply_defaults(config_obj, CONFIG_JSON_SCHEMA)
    validate_config_extra(config)


def test_does_not_contain_defaults():
    """Due to the way our merging works, if this schema has any defaults they
    will clobber potentially useful values in the backing manifest. #227
    """
    to_process = [(CONFIG_JSON_SCHEMA, ())]
    while to_process:
        schema, route = to_process.pop()
        # Check this value
        if isinstance(schema, dict):
            if 'default' in schema:
                raise AssertionError(
                    'Unexpected default in schema at {0}'.format(
                        ' => '.join(route),
                    )
                )

            for key, value in schema.items():
                to_process.append((value, route + (key,)))
