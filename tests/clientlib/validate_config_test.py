import pytest

from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import InvalidConfigError
from pre_commit.clientlib.validate_config import run
from pre_commit.clientlib.validate_config import validate_config_extra
from pre_commit.jsonschema_extensions import apply_defaults
from testing.util import is_valid_according_to_schema


def test_returns_0_for_valid_config():
    assert run(['example_pre-commit-config.yaml']) == 0


def test_returns_0_for_out_manifest():
    assert run([]) == 0


def test_returns_1_for_failing():
    assert run(['tests/data/valid_yaml_but_invalid_config.yaml']) == 1


@pytest.mark.parametrize(('manifest_obj', 'expected'), (
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
def test_is_valid_according_to_schema(manifest_obj, expected):
    ret = is_valid_according_to_schema(manifest_obj, CONFIG_JSON_SCHEMA)
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
