
import jsonschema
import jsonschema.exceptions
import pytest

from pre_commit.clientlib.validate_config import CONFIG_JSON_SCHEMA
from pre_commit.clientlib.validate_config import run


def test_returns_0_for_valid_config():
    assert run(['example_pre-commit-config.yaml']) == 0


def test_returns_0_for_out_manifest():
    assert run([]) == 0


def test_returns_1_for_failing():
    assert run(['tests/data/valid_yaml_but_invalid_config.yaml']) == 1

def is_valid_according_to_schema(obj, schema):
    try:
        jsonschema.validate(obj, schema)
        return True
    except jsonschema.exceptions.ValidationError:
        return False


@pytest.mark.parametrize(('manifest_obj', 'expected'), (
    ([], False),
    (
        [{
          'repo': 'git@github.com:pre-commit/pre-commit-hooks',
          'sha': 'cd74dc150c142c3be70b24eaf0b02cae9d235f37',
          'hooks': [
              {
                  'id': 'pyflakes',
                  'files': '*.py',
              }
          ]
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
                  'files': '*.py',
                  'args': ['foo', 'bar', 'baz'],
              }
          ]
        }],
        True,
    ),
))
def test_is_valid_according_to_schema(manifest_obj, expected):
    ret = is_valid_according_to_schema(manifest_obj, CONFIG_JSON_SCHEMA)
    assert ret is expected