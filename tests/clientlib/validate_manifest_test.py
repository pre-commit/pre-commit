import pytest

from pre_commit.clientlib.validate_manifest import additional_manifest_check
from pre_commit.clientlib.validate_manifest import InvalidManifestError
from pre_commit.clientlib.validate_manifest import MANIFEST_JSON_SCHEMA
from pre_commit.clientlib.validate_manifest import run
from testing.util import is_valid_according_to_schema


def test_returns_0_for_valid_manifest():
    assert run(['example_hooks.yaml']) == 0


def test_returns_0_for_our_manifest():
    assert run([]) == 0


def test_returns_1_for_failing():
    assert run(['tests/data/valid_yaml_but_invalid_manifest.yaml']) == 1


def test_additional_manifest_check_raises_for_bad_language():
    with pytest.raises(InvalidManifestError):
        additional_manifest_check([{'id': 'foo', 'language': 'not valid'}])


@pytest.mark.parametrize(('obj'), (
    [{'language': 'python'}],
    [{'language': 'ruby'}],
))
def test_additional_manifest_check_languages(obj):
    additional_manifest_check(obj)


@pytest.mark.parametrize(('manifest_obj', 'expected'), (
    ([], False),
    ([{'id': 'a', 'name': 'b', 'entry': 'c', 'language': 'python'}], True),
    (
        [{
            'id': 'a',
            'name': 'b',
            'entry': 'c',
            'language': 'python',
            'expected_return_value': 0,
        }],
        True,
    ),
))
def test_is_valid_according_to_schema(manifest_obj, expected):
    ret = is_valid_according_to_schema(manifest_obj, MANIFEST_JSON_SCHEMA)
    assert ret is expected
